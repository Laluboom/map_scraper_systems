"""Run once: python3 make_guide_pdf.py  ->  produces SETUP_GUIDE.pdf"""
from fpdf import FPDF
from fpdf.enums import XPos, YPos

class PDF(FPDF):
    def header(self):
        self.set_font("Helvetica", "B", 11)
        self.set_fill_color(21, 101, 192)
        self.set_text_color(255, 255, 255)
        self.rect(0, 0, 210, 14, "F")
        self.set_xy(0, 2)
        self.cell(0, 10, "Supplier Scraper - Client Setup Guide", align="C")
        self.set_text_color(0, 0, 0)
        self.ln(12)

    def footer(self):
        self.set_y(-12)
        self.set_font("Helvetica", "I", 8)
        self.set_text_color(150, 150, 150)
        self.cell(0, 10, f"Page {self.page_no()}", align="C")

    def section(self, title):
        self.ln(4)
        self.set_font("Helvetica", "B", 11)
        self.set_fill_color(227, 234, 247)
        self.set_text_color(21, 101, 192)
        self.cell(0, 8, title, new_x=XPos.LMARGIN, new_y=YPos.NEXT, fill=True)
        self.set_text_color(0, 0, 0)
        self.ln(1)

    def body(self, text):
        self.set_font("Helvetica", "", 10)
        self.multi_cell(0, 6, text)
        self.ln(1)

    def note(self, text):
        self.set_font("Helvetica", "I", 9)
        self.set_text_color(80, 80, 80)
        self.multi_cell(0, 5, text)
        self.set_text_color(0, 0, 0)
        self.ln(1)

    def table(self, headers, rows):
        self.set_font("Helvetica", "B", 9)
        self.set_fill_color(200, 210, 235)
        col_w = [75, 110]
        for i, h in enumerate(headers):
            self.cell(col_w[i], 7, h, border=1, fill=True)
        self.ln()
        self.set_font("Helvetica", "", 9)
        fill = False
        for row in rows:
            self.set_fill_color(245, 247, 252) if fill else self.set_fill_color(255, 255, 255)
            # track row start y to align cells
            y_start = self.get_y()
            x_start = self.get_x()
            # first column
            self.multi_cell(col_w[0], 6, row[0], border=1, fill=True)
            y_end = self.get_y()
            # second column at same y
            self.set_xy(x_start + col_w[0], y_start)
            self.multi_cell(col_w[1], 6, row[1], border=1, fill=True)
            self.set_xy(x_start, max(y_end, self.get_y()))
            fill = not fill
        self.ln(2)

    def code(self, text):
        self.set_font("Courier", "", 9)
        self.set_fill_color(240, 240, 240)
        self.set_draw_color(200, 200, 200)
        self.multi_cell(0, 5, text, fill=True, border=1)
        self.set_draw_color(0, 0, 0)
        self.ln(2)


pdf = PDF()
pdf.set_margins(18, 18, 18)
pdf.set_auto_page_break(auto=True, margin=18)
pdf.add_page()

# Title block
pdf.set_font("Helvetica", "B", 16)
pdf.set_text_color(21, 101, 192)
pdf.ln(2)
pdf.cell(0, 10, "Supplier Scraper", new_x=XPos.LMARGIN, new_y=YPos.NEXT, align="C")
pdf.set_font("Helvetica", "", 11)
pdf.set_text_color(80, 80, 80)
pdf.cell(0, 7, "Step-by-step setup guide for new installations", new_x=XPos.LMARGIN, new_y=YPos.NEXT, align="C")
pdf.set_text_color(0, 0, 0)
pdf.ln(6)

# What you need
pdf.section("What you need before starting")
pdf.body(
    "  - A Gmail account to send emails from\n"
    "  - Your Google Places API key  (provided by Schion)\n"
    "  - The zip file:  supplier_scraper_v1.0.0.zip"
)

# Step 1
pdf.section("Step 1 - Extract the zip")
pdf.body("Right-click the zip file -> Extract All -> extract to a folder you will keep.\nExample:  C:\\SupplierScraper\\")
pdf.body("After extracting you should see:")
pdf.code("  supplier_scraper.exe\n  config.ini\n  README.md")

# Step 2
pdf.section("Step 2 - Create a Gmail App Password")
pdf.note("Skip this step if Schion has provided you a pre-filled config.ini.")
pdf.body(
    "Your Gmail needs an App Password - a special code so the app can send emails on your behalf.\n\n"
    "1.  Go to:  myaccount.google.com/apppasswords\n"
    "    (You must have 2-Step Verification enabled. If not, enable it first at myaccount.google.com/security)\n\n"
    "2.  App name: type  Supplier Scraper  -> click Create\n\n"
    "3.  Copy the 16-character code shown  (e.g. abcd efgh ijkl mnop)\n"
    "    Save it - it only shows once."
)

# Step 3
pdf.section("Step 3 - Run setup")
pdf.body("Double-click  supplier_scraper.exe  - a black terminal window opens.\nType the following and press Enter:")
pdf.code("  setup")
pdf.body("Follow the prompts:")
pdf.table(
    ["Prompt", "What to enter"],
    [
        ["Google Places API Key", "Provided by Schion"],
        ["SMTP host", "smtp.gmail.com  (press Enter for default)"],
        ["Your email address", "Your Gmail address"],
        ["Password", "The 16-character App Password from Step 2"],
        ["Sender display name", "John Doe  (press Enter for default)"],
    ]
)

# Step 4
pdf.section("Step 4 - Open the dashboard")
pdf.body("Double-click  supplier_scraper.exe  again, type the following and press Enter:")
pdf.code("  serve")
pdf.body("Then open your web browser and go to:")
pdf.code("  http://localhost:8080")
pdf.body("The dashboard is now running. Keep the terminal window open while you use it.")

# Step 5
pdf.section("Step 5 - Daily workflow")
pdf.table(
    ["Page", "What to do"],
    [
        ["Scrape", "Pick a city and click Scrape to find new companies"],
        ["Contacts", "Review results, click Approve on companies to contact"],
        ["Send Emails", "Click Send Campaign to email all approved contacts"],
        ["Logs", "See who was sent, who bounced"],
    ]
)

# Troubleshooting
pdf.section("Troubleshooting")
pdf.table(
    ["Problem", "Fix"],
    [
        ["SMTP credentials not configured", "Re-run setup and enter your email + App Password"],
        ["Emails not sending", "Make sure you used the App Password, not your regular Gmail password"],
        ["Dashboard won't open", "Keep the terminal window open (must show 'Uvicorn running')"],
        ["Black window closes instantly", "Right-click supplier_scraper.exe -> Run as Administrator"],
    ]
)

# Updates
pdf.section("Getting updates")
pdf.body(
    "When a new version is available, a yellow banner will appear at the top of the dashboard "
    "with a download link.\n\n"
    "Download the new .exe and replace the old one in your folder. "
    "Your data and settings stay the same."
)

out = "SETUP_GUIDE.pdf"
pdf.output(out)
print(f"Saved: {out}")

from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail
from app.config import settings

EMAIL_SUBJECT = "Inquiry for Non-Ferrous Scrap Supply"

EMAIL_BODY_TEMPLATE = """\
Dear {greeting},

We are an ISO & EPA certified recycle company based in Pakistan.
We are currently buying Non-ferrous scrap from companies in the US, EU & UK \
region and would like to know if you can offer us the below mentioned items \
on a regular basis:

* Sealed Units scrap
* Electric motors scrap
* Battery Scrap
* Aluminum cables
* Copper cables

We take approx. 1,200 M.tons/month of each item and would like to know if \
you can offer any of the material regularly.
We are one of the few companies certified by the EPA to import battery scrap.

We await your reply.

Best regards,
Noaman Alam
Manager (Purchasing)
SCHION INTERNATIONAL
Tel: +92 21 32570013
Cell: +92 33 33 44 99 59
Mail: Noaman@schion.com.pk
Web: www.schion.com.pk

--
To unsubscribe from future emails, reply with "UNSUBSCRIBE" in the subject line.
"""


def build_email_body(company_name: str | None) -> str:
    greeting = company_name if company_name else "Sir"
    return EMAIL_BODY_TEMPLATE.format(greeting=greeting)


def send_email(to_email: str, company_name: str | None) -> dict:
    """Send one email via SendGrid. Returns dict with message_id or error."""
    body = build_email_body(company_name)
    message = Mail(
        from_email=(settings.sendgrid_from_email, settings.sendgrid_from_name),
        to_emails=to_email,
        subject=EMAIL_SUBJECT,
        plain_text_content=body,
    )
    try:
        sg = SendGridAPIClient(settings.sendgrid_api_key)
        response = sg.send(message)
        message_id = response.headers.get("X-Message-Id", "")
        return {"success": True, "message_id": message_id}
    except Exception as exc:
        return {"success": False, "error": str(exc)}


# --- AWS SES fallback (PH-004) ---
# Uncomment and configure if switching from SendGrid to SES:
#
# import boto3
# def send_email_ses(to_email: str, company_name: str | None) -> dict:
#     body = build_email_body(company_name)
#     client = boto3.client(
#         "ses",
#         aws_access_key_id=settings.aws_ses_access_key,
#         aws_secret_access_key=settings.aws_ses_secret_key,
#         region_name=settings.aws_ses_region,
#     )
#     try:
#         resp = client.send_email(
#             Source=settings.sendgrid_from_email,
#             Destination={"ToAddresses": [to_email]},
#             Message={
#                 "Subject": {"Data": EMAIL_SUBJECT},
#                 "Body": {"Text": {"Data": body}},
#             },
#         )
#         return {"success": True, "message_id": resp["MessageId"]}
#     except Exception as exc:
#         return {"success": False, "error": str(exc)}

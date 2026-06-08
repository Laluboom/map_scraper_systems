# PyInstaller spec file — run: pyinstaller supplier_scraper.spec
# This builds supplier_scraper.exe in the dist/ folder.

import sys
from pathlib import Path

block_cipher = None
HERE = Path(SPECPATH)

a = Analysis(
    [str(HERE / "cli.py")],
    pathex=[str(HERE)],
    binaries=[],
    datas=[
        (str(HERE / "templates"), "templates"),
        (str(HERE / "config.ini.example"), "."),
    ],
    hiddenimports=[
        # FastAPI / Starlette internals
        "uvicorn.logging",
        "uvicorn.loops",
        "uvicorn.loops.auto",
        "uvicorn.protocols",
        "uvicorn.protocols.http",
        "uvicorn.protocols.http.auto",
        "uvicorn.protocols.websockets",
        "uvicorn.protocols.websockets.auto",
        "uvicorn.lifespan",
        "uvicorn.lifespan.on",
        "starlette.templating",
        "jinja2",
        # SQLAlchemy
        "sqlalchemy.dialects.sqlite",
        # Scrapy
        "scrapy.utils.misc",
        "scrapy.extensions",
        "scrapy.pipelines",
        "twisted",
        "twisted.internet.asyncioreactor",
        # email
        "sendgrid",
        "httpx",
        # local modules
        "db",
        "models",
        "email_sender",
        "validator",
        "prioritizer",
        "scraper_runner",
        "web_server",
    ],
    hookspath=[],
    runtime_hooks=[],
    excludes=["tkinter", "matplotlib", "numpy", "pandas"],
    cipher=block_cipher,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    name="supplier_scraper",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=True,        # keeps a terminal window — needed to see scrape progress
    icon=None,           # set to an .ico file path if you want a custom icon
)

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.routers import traders, campaigns, logs, scrape

app = FastAPI(title="Supplier Scraper API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],  # add production frontend URL when deployed
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(traders.router, prefix="/traders", tags=["traders"])
app.include_router(campaigns.router, prefix="/campaigns", tags=["campaigns"])
app.include_router(logs.router, prefix="/logs", tags=["logs"])
app.include_router(scrape.router, prefix="/scrape", tags=["scrape"])


@app.get("/health")
def health():
    return {"status": "ok"}

from fastapi import APIRouter
from app.schemas import ScrapeStartRequest
from app.tasks.scrape_tasks import run_spider

VALID_SOURCES = [
    "isri", "bir", "cari", "yellowpages", "kompass",
    "europages", "thomasnet", "scrapmonster", "recycling_intl", "epa",
]

router = APIRouter()


@router.post("/start")
def start_scrape(payload: ScrapeStartRequest):
    if payload.source not in VALID_SOURCES:
        return {"error": f"Unknown source. Valid: {VALID_SOURCES}"}
    task = run_spider.delay(payload.source, payload.regions or [])
    return {"task_id": task.id, "source": payload.source, "status": "queued"}

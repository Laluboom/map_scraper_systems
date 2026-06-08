"""
Tracks which city+search_term combinations have been scraped.
Enables --resume: skip areas done within rescrape_days.
"""
from datetime import datetime, timedelta
from sqlalchemy.orm import Session


def _area_id(city: str, state: str, term: str) -> str:
    return f"{city.strip()}|{state.strip()}|{term.strip()}"


def is_done(db: Session, city: str, state: str, term: str, rescrape_days: int = 30) -> bool:
    from models import ScrapedArea
    row = db.query(ScrapedArea).filter(
        ScrapedArea.id == _area_id(city, state, term)
    ).first()
    if not row:
        return False
    if rescrape_days == 0:
        return False
    return row.scraped_at >= datetime.utcnow() - timedelta(days=rescrape_days)


def mark_done(db: Session, city: str, state: str, term: str, result_count: int = 0):
    from models import ScrapedArea
    area_id = _area_id(city, state, term)
    row = db.query(ScrapedArea).filter(ScrapedArea.id == area_id).first()
    if row:
        row.scraped_at = datetime.utcnow()
        row.result_count = result_count
    else:
        db.add(ScrapedArea(
            id=area_id,
            scraped_at=datetime.utcnow(),
            result_count=result_count,
        ))
    db.commit()


def get_progress(db: Session, total_areas: int) -> dict:
    from models import ScrapedArea
    done = db.query(ScrapedArea).count()
    return {
        "done": done,
        "total": total_areas,
        "pct": round(100 * done / total_areas, 1) if total_areas else 0,
    }

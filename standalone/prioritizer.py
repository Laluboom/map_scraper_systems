PRIORITY_KEYWORDS = [
    "sealed unit", "sealed units",
    "compressor scrap", "ac compressor", "fridge compressor",
    "electric motor", "electric motors",
    "battery scrap", "lead battery", "lithium battery",
    "aluminum cable", "aluminium cable",
    "copper cable",
]


def extract_tags(text: str) -> list[str]:
    low = text.lower()
    return list({kw for kw in PRIORITY_KEYWORDS if kw in low})


def is_priority(tags: list[str]) -> bool:
    return len(tags) > 0

PRIORITY_KEYWORDS = [
    "sealed unit", "sealed units",
    "compressor scrap", "ac compressor", "fridge compressor", "refrigerator compressor",
    "electric motor", "electric motors",
    "battery scrap", "lead battery", "lithium battery",
    "aluminum cable", "aluminium cable",
    "copper cable",
]


def extract_product_tags(text: str) -> list[str]:
    text_lower = text.lower()
    found = []
    for keyword in PRIORITY_KEYWORDS:
        if keyword in text_lower:
            found.append(keyword)
    return list(set(found))


def is_priority(product_tags: list[str]) -> bool:
    return len(product_tags) > 0

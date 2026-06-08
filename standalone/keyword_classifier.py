"""
3-layer company scoring (0-100).
Layer 1 — company name keywords  (+30)
Layer 2 — Google Maps place types (+40 high / +20 secondary)
Layer 3 — website text keywords   (+30)
"""

COMPANY_NAME_KEYWORDS = [
    "scrap", "recycl", "metal", "copper", "aluminum", "aluminium",
    "cable", "wire", "motor", "battery", "compressor", "salvage",
    "junk", "surplus", "non-ferrous", "nonferrous", "smelter",
]

HIGH_PRIORITY_TYPES = {
    "recycling_center", "scrap_yard",
}

SECONDARY_PRIORITY_TYPES = {
    "metal_supplier", "waste_management_service",
    "electrical_supply_store", "industrial_supplier",
    "wholesale_store",
}

PRODUCT_KEYWORDS = [
    "sealed unit", "sealed units",
    "compressor scrap", "ac compressor", "fridge compressor",
    "electric motor", "electric motors",
    "battery scrap", "lead battery", "lithium battery",
    "aluminum cable", "aluminium cable",
    "copper cable",
]


def score_company(name: str, google_types: list, website_text: str) -> tuple[int, list[str]]:
    """Return (score 0-100, matched tags list)."""
    score = 0
    tags = []

    # Layer 1: company name
    name_lower = name.lower()
    for kw in COMPANY_NAME_KEYWORDS:
        if kw in name_lower:
            score += 30
            tags.append(kw)
            break  # only count once per layer

    # Layer 2: Google place types
    types_lower = [t.lower() for t in (google_types or [])]
    if any(t in HIGH_PRIORITY_TYPES for t in types_lower):
        score += 40
        tags.append("recycling_center")
    elif any(t in SECONDARY_PRIORITY_TYPES for t in types_lower):
        score += 20
        tags.append("industrial_supplier")

    # Layer 3: website text
    text_lower = website_text.lower()
    matched_products = [kw for kw in PRODUCT_KEYWORDS if kw in text_lower]
    if matched_products:
        score += 30
        tags.extend(matched_products)

    return min(score, 100), list(set(tags))


def is_priority(score: int, threshold: int = 40) -> bool:
    return score >= threshold

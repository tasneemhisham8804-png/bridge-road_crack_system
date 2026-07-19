"""
pci_scoring.py
---------------
Converts a list of detected road distresses into a single 0-100 Pavement
Condition Index (PCI) score for a road segment.

This is ASTM D6433-*inspired*: same category thresholds and the same idea
of distress-type/severity-weighted deducts, but the deduct values below
are our own calibration -- not a reproduction of the licensed ASTM
nonlinear deduct curves. State this plainly if asked (see plan doc).

"manhole" is never scored as a distress; it's a landmark/context class
used only to flag nearby cracking (see main.py's manhole-proximity rule).
"""

SEVERITY_LOW = 1
SEVERITY_MEDIUM = 2
SEVERITY_HIGH = 3

_SEVERITY_KEY = {SEVERITY_LOW: "low", SEVERITY_MEDIUM: "medium", SEVERITY_HIGH: "high"}

# Our own calibrated deduct values per distress type + severity.
# Higher deduct = more damage to the PCI score.
DEDUCT_TABLE = {
    "pothole": {"low": 8, "medium": 15, "high": 25},
    "alligator_crack": {"low": 6, "medium": 12, "high": 20},
    "longitudinal_crack": {"low": 3, "medium": 7, "high": 12},
    "transverse_crack": {"low": 3, "medium": 7, "high": 12},
}

# Extra deduct applied when a crack/pothole is flagged near_manhole --
# utility trenches around manholes are common failure points, so we
# treat this as a modest severity-independent penalty on top of the
# base deduct rather than bumping the severity level itself.
NEAR_MANHOLE_EXTRA_DEDUCT = 3

# ASTM-style condition categories
PCI_CATEGORIES = [
    (86, 100, "Good", "جيدة"),
    (71, 85, "Satisfactory", "مقبولة"),
    (56, 70, "Fair", "متوسطة"),
    (41, 55, "Poor", "سيئة"),
    (26, 40, "Very Poor", "سيئة جداً"),
    (0, 25, "Failed", "فاشلة"),
]


def deduct_for_distress(distress_type: str, severity_level: int, near_manhole: bool = False) -> float:
    """Deduct value for a single distress. Returns 0 for non-scored types (e.g. manhole)."""
    severity_key = _SEVERITY_KEY.get(severity_level)
    if distress_type not in DEDUCT_TABLE or severity_key is None:
        return 0.0
    deduct = DEDUCT_TABLE[distress_type][severity_key]
    if near_manhole:
        deduct += NEAR_MANHOLE_EXTRA_DEDUCT
    return deduct


def category_for_score(score: float):
    """Returns (category_en, category_ar) for a given PCI score."""
    for low, high, en, ar in PCI_CATEGORIES:
        if low <= score <= high:
            return en, ar
    return "Failed", "فاشلة"  # fallback for any out-of-range score


def compute_pci(distresses: list) -> dict:
    """
    distresses: list of dicts, each with at least:
        distress_type (str), severity_level (int|None), near_manhole (bool)

    Returns:
        {
            "pci_score": float (0-100),
            "category_en": str,
            "category_ar": str,
            "total_deducts": float,
            "message_en": str,
            "message_ar": str,
        }

    Note: this is a simplified sum-of-deducts model, clamped to [0, 100].
    ASTM's real methodology applies a nonlinear correction curve when many
    high deducts combine (diminishing marginal damage) -- we skip that
    correction here and state so; see plan doc "Open Items".
    """
    total_deducts = sum(
        deduct_for_distress(
            d.get("distress_type"),
            d.get("severity_level"),
            bool(d.get("near_manhole")),
        )
        for d in distresses
    )

    score = max(0.0, min(100.0, 100.0 - total_deducts))
    category_en, category_ar = category_for_score(score)

    return {
        "pci_score": round(score, 1),
        "category_en": category_en,
        "category_ar": category_ar,
        "total_deducts": round(total_deducts, 1),
        "message_en": f"Segment condition score: {round(score, 1)} — {category_en}",
        "message_ar": f"درجة حالة القطعة: {round(score, 1)} — {category_ar}",
    }

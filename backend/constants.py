"""Shared application constants."""

# Critical area threshold used by predictive maintenance.
# Matches severity_level=3 boundary: width≈150, height≈70 → area≈10500
CRITICAL_AREA_THRESHOLD = 10500

# Max pixel distance between bounding-box centers to be considered the same crack
CRACK_MATCH_DISTANCE_THRESHOLD = 40

# Bucket size (pixels) for generating default crack identifiers
CRACK_IDENTIFIER_BUCKET_SIZE = 50

# ─────────────────────────────────────────────────────────────────
# Road distress severity & manhole-proximity thresholds. Our own
# calibration on YOLO pixel bounding boxes (see road_crack_plan_.md
# Feature 1), not a literal reproduction of ASTM's qualitative criteria.
# ─────────────────────────────────────────────────────────────────

ROAD_SEVERITY_LOW = 1
ROAD_SEVERITY_MEDIUM = 2
ROAD_SEVERITY_HIGH = 3

CRACK_LENGTH_THRESHOLDS = {"medium": 80, "high": 200}
ALLIGATOR_AREA_THRESHOLDS = {"medium": 3000, "high": 8000}
POTHOLE_AREA_THRESHOLDS = {"medium": 2000, "high": 6000}

# Max pixel distance between a crack/pothole's center and a manhole's
# center for it to be flagged "near manhole" (utility-trench context).
MANHOLE_PROXIMITY_THRESHOLD = 150

CRACK_TYPES = {"longitudinal_crack", "transverse_crack"}
AREA_SCORED_ROAD_TYPES = {"alligator_crack", "pothole"}

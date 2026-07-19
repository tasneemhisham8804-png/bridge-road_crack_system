import io
import logging
import os

from PIL import Image

from constants import (
    ROAD_SEVERITY_HIGH,
    ROAD_SEVERITY_LOW,
    ROAD_SEVERITY_MEDIUM,
    CRACK_LENGTH_THRESHOLDS,
    ALLIGATOR_AREA_THRESHOLDS,
    POTHOLE_AREA_THRESHOLDS,
    MANHOLE_PROXIMITY_THRESHOLD,
    CRACK_TYPES,
    AREA_SCORED_ROAD_TYPES,
)

logger = logging.getLogger(__name__)

_model = None


def _get_model():
    """Lazy-load YOLO model — reuses the same weights as bridge crack
    detection (services/prediction.py), since rdd.yaml's classes already
    cover road distress types (cracks, potholes, manholes). Loaded
    separately here (rather than importing prediction._get_model) to keep
    this module independent and avoid coupling to a private symbol."""
    global _model
    if _model is None:
        from ultralytics import YOLO

        model_path = os.path.abspath(
            os.path.join(os.path.dirname(__file__), "../../yolo_model/best1.pt")
        )
        if not os.path.exists(model_path):
            raise FileNotFoundError(f"YOLO model weights not found at {model_path}")
        _model = YOLO(model_path)
        logger.info("YOLO model loaded for road detection from %s", model_path)
    return _model


def classify_road_severity(distress_type: str, width: float, height: float) -> int | None:
    """Returns 1 (Low) / 2 (Medium) / 3 (High), or None for non-scored
    classes like 'manhole' which is a landmark, not a distress."""
    if distress_type in CRACK_TYPES:
        length = max(width, height)
        if length >= CRACK_LENGTH_THRESHOLDS["high"]:
            return ROAD_SEVERITY_HIGH
        if length >= CRACK_LENGTH_THRESHOLDS["medium"]:
            return ROAD_SEVERITY_MEDIUM
        return ROAD_SEVERITY_LOW

    if distress_type == "alligator_crack":
        area = width * height
        if area >= ALLIGATOR_AREA_THRESHOLDS["high"]:
            return ROAD_SEVERITY_HIGH
        if area >= ALLIGATOR_AREA_THRESHOLDS["medium"]:
            return ROAD_SEVERITY_MEDIUM
        return ROAD_SEVERITY_LOW

    if distress_type == "pothole":
        area = width * height
        if area >= POTHOLE_AREA_THRESHOLDS["high"]:
            return ROAD_SEVERITY_HIGH
        if area >= POTHOLE_AREA_THRESHOLDS["medium"]:
            return ROAD_SEVERITY_MEDIUM
        return ROAD_SEVERITY_LOW

    return None  # manhole or unrecognized class


def apply_manhole_proximity(distresses: list[dict]) -> list[dict]:
    """
    Given all raw distresses detected in ONE image, flags crack/pothole
    distresses that sit close to a manhole detection: sets near_manhole=True
    and bumps severity up one level (capped at High). Manhole entries
    themselves are left untouched (they're a landmark, not a scored distress).
    """
    manholes = [d for d in distresses if d["distress_type"] == "manhole"]
    if not manholes:
        for d in distresses:
            d["near_manhole"] = False
        return distresses

    for d in distresses:
        if d["distress_type"] not in CRACK_TYPES | AREA_SCORED_ROAD_TYPES:
            d["near_manhole"] = False
            continue
        is_near = any(
            ((d["x"] - m["x"]) ** 2 + (d["y"] - m["y"]) ** 2) ** 0.5 < MANHOLE_PROXIMITY_THRESHOLD
            for m in manholes
        )
        d["near_manhole"] = is_near
        if is_near and d["severity"] is not None:
            d["severity"] = min(ROAD_SEVERITY_HIGH, d["severity"] + 1)

    return distresses


def detect_road_distress_with_yolo(contents: bytes) -> list[dict]:
    img = Image.open(io.BytesIO(contents))
    model = _get_model()
    results = model(img)

    distresses = []
    for result in results:
        for box in result.boxes:
            x_center, y_center, width, height = box.xywh[0].tolist()
            confidence = float(box.conf[0])
            class_id = int(box.cls[0])
            class_name = model.names[class_id]

            distresses.append({
                "x": x_center,
                "y": y_center,
                "width": width,
                "height": height,
                "confidence": confidence,
                "distress_type": class_name,
                "severity": classify_road_severity(class_name, width, height),
            })

    return apply_manhole_proximity(distresses)

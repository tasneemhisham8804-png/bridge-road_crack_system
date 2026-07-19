import logging
from typing import List

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, status
from sqlalchemy.orm import Session

from database import get_db
from deps import get_current_active_user, get_road_segment_or_404
from models import RoadSegment, RoadDistressDetection, RoadInspectionReport
from pci_scoring import compute_pci, category_for_score
from schemas import (
    RoadDetectResponse,
    RoadDistressBase,
    RoadMapResponse,
    RoadPCIResponse,
    RoadSaveResponse,
    RoadSegmentCreate,
    RoadSegmentCreateResponse,
    RoadSegmentListResponse,
)
from services.roads import detect_road_distress_with_yolo
from utils.uploads import read_validated_image

logger = logging.getLogger(__name__)

router = APIRouter(
    tags=["roads"],
)


@router.post("/road-segments", response_model=RoadSegmentCreateResponse)
async def create_road_segment(
    payload: RoadSegmentCreate,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_active_user),
):
    segment = RoadSegment(
        segment_name=payload.segment_name,
        road_name=payload.road_name,
        city=payload.city,
        latitude=payload.latitude,
        longitude=payload.longitude,
    )
    db.add(segment)
    db.commit()
    db.refresh(segment)
    return {"id": segment.id, "name": segment.segment_name, "city": segment.city}


@router.get("/road-segments", response_model=RoadSegmentListResponse)
async def get_road_segments(
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_active_user),
):
    segments = db.query(RoadSegment).order_by(RoadSegment.segment_name.asc()).all()
    return {
        "segments": [
            {"id": s.id, "name": s.segment_name, "road_name": s.road_name, "city": s.city}
            for s in segments
        ]
    }


@router.post("/road-detect", response_model=RoadDetectResponse)
async def detect_road_distress(
    image: UploadFile = File(...),
    current_user: dict = Depends(get_current_active_user),
):
    """Runs the same YOLO model used for bridge cracks — rdd.yaml's classes
    (longitudinal_crack, transverse_crack, alligator_crack, pothole, manhole)
    are already road-distress classes, so no separate model is needed."""
    try:
        contents = await read_validated_image(image)
        distresses = detect_road_distress_with_yolo(contents)
        return {"distresses": distresses}
    except HTTPException:
        raise
    except FileNotFoundError as e:
        logger.exception("YOLO model not available")
        return {"error": str(e), "distresses": []}
    except Exception as e:
        logger.exception("Road detection error")
        return {"error": str(e), "distresses": []}


@router.post("/road-detect/{segment_id}/save", response_model=RoadSaveResponse)
async def save_road_detections(
    distresses: List[RoadDistressBase],
    segment: RoadSegment = Depends(get_road_segment_or_404),
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_active_user),
):
    if not distresses:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="At least one distress is required")

    try:
        distress_dicts = [d.model_dump() for d in distresses]
        pothole_count = len([d for d in distress_dicts if d["distress_type"] == "pothole"])

        report = RoadInspectionReport(
            segment_id=segment.id,
            total_distresses_detected=len(distress_dicts),
            pothole_count=pothole_count,
            created_by=int(current_user["sub"]),
            status="Pending",
        )
        db.add(report)
        db.flush()  # report.id now exists

        for d in distress_dicts:
            db.add(RoadDistressDetection(
                segment_id=segment.id,
                report_id=report.id,
                x=d["x"], y=d["y"], width=d["width"], height=d["height"],
                area=d["width"] * d["height"],
                confidence=d["confidence"],
                distress_type=d["distress_type"],
                severity_level=d["severity"],
                near_manhole=bool(d["near_manhole"]),
            ))

        pci = compute_pci([
            {"distress_type": d["distress_type"], "severity_level": d["severity"], "near_manhole": d["near_manhole"]}
            for d in distress_dicts
        ])
        report.pci_score = pci["pci_score"]
        report.pci_category = pci["category_en"]

        db.commit()

        return {
            "message": "Road detections saved successfully",
            "report_id": report.id,
            "pothole_count": pothole_count,
            **pci,
        }
    except HTTPException:
        raise
    except Exception:
        db.rollback()
        logger.exception("Error saving road detections")
        raise HTTPException(status_code=500, detail="Failed to save detections. Please try again.")


@router.get("/road-segment/{segment_id}/pci", response_model=RoadPCIResponse)
async def get_road_segment_pci(
    segment: RoadSegment = Depends(get_road_segment_or_404),
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_active_user),
):
    """Returns the PCI score from the segment's most recent inspection report."""
    latest_report = (
        db.query(RoadInspectionReport)
        .filter(RoadInspectionReport.segment_id == segment.id)
        .order_by(RoadInspectionReport.report_date.desc())
        .first()
    )
    if not latest_report or latest_report.pci_score is None:
        raise HTTPException(status_code=404, detail="No inspection data available for this segment yet")

    _, category_ar = category_for_score(latest_report.pci_score)

    return {
        "segment_name": segment.segment_name,
        "pci_score": latest_report.pci_score,
        "category_en": latest_report.pci_category,
        "category_ar": category_ar,
        "pothole_count": latest_report.pothole_count,
        "total_distresses": latest_report.total_distresses_detected,
        "report_date": latest_report.report_date.isoformat(),
        "message_en": f"Segment condition score: {latest_report.pci_score} — {latest_report.pci_category}",
        "message_ar": f"درجة حالة القطعة: {latest_report.pci_score} — {category_ar}",
    }


@router.get("/road-segments/map", response_model=RoadMapResponse)
async def get_road_segments_map(
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_active_user),
):
    """Single endpoint for the road network map — mirrors /bridges/map."""
    segments = db.query(RoadSegment).all()
    result = []
    for segment in segments:
        latest_report = (
            db.query(RoadInspectionReport)
            .filter(RoadInspectionReport.segment_id == segment.id)
            .order_by(RoadInspectionReport.report_date.desc())
            .first()
        )
        result.append({
            "id": segment.id,
            "name": segment.segment_name,
            "road_name": segment.road_name,
            "city": segment.city,
            "latitude": segment.latitude,
            "longitude": segment.longitude,
            "pci_score": latest_report.pci_score if latest_report else None,
            "pci_category": latest_report.pci_category if latest_report else None,
            "pothole_count": latest_report.pothole_count if latest_report else 0,
            "total_distresses": latest_report.total_distresses_detected if latest_report else 0,
        })

    return {"segments": result}

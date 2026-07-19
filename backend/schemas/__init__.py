from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class GoogleLoginRequest(BaseModel):
    credential: str


class GoogleLoginResponse(BaseModel):
    token: str
    user: Dict[str, Any]


class CrackBase(BaseModel):
    x: float = Field(..., ge=0)
    y: float = Field(..., ge=0)
    width: float = Field(..., gt=0)
    height: float = Field(..., gt=0)
    confidence: float = Field(..., ge=0, le=1)
    severity: int = Field(..., ge=1, le=3)
    crack_type: str = Field(..., min_length=1, max_length=100)


class CrackSaveRequest(BaseModel):
    cracks: List[CrackBase]


class CrackDetectResponse(BaseModel):
    cracks: List[CrackBase] = Field(default_factory=list)
    error: Optional[str] = None


class CrackSaveResponse(BaseModel):
    message: Optional[str] = None
    report_id: Optional[int] = None
    significant_growth_count: Optional[int] = None
    saved_crack_ids: Optional[List[int]] = None
    error: Optional[str] = None


class CrackGrowthEntry(BaseModel):
    id: int
    x: float
    y: float
    width: float
    height: float
    area: float
    confidence: float
    severity_level: int
    crack_type: str
    detected_at: str
    growth: Optional[Dict[str, Any]] = None


class CrackGrowthResponse(BaseModel):
    bridge_name: str
    crack_history: Dict[str, List[CrackGrowthEntry]]
    total_tracked_cracks: int = 0


class CrackHistoryEntry(BaseModel):
    id: int
    detected_at: str
    area: float
    width: float
    height: float
    confidence: float
    severity_level: int


class CrackHistoryResponse(BaseModel):
    crack_identifier: Optional[str] = None
    inspection_count: int
    growth_pct: Optional[float] = None
    growth_per_day: Optional[float] = None
    history: List[CrackHistoryEntry]


class CrackPredictionResponse(BaseModel):
    status: str
    message_en: Optional[str] = None
    message_ar: Optional[str] = None
    recommended_inspection_date: Optional[str] = None
    days_to_critical: Optional[int] = None
    current_area: Optional[float] = None
    growth_per_day: Optional[float] = None


class SensorDataResponse(BaseModel):
    temperature_history: List[Optional[float]]
    moisture_history: List[Optional[float]]
    vibration_history: List[Optional[float]]
    strain_history: List[Optional[float]]
    timestamps: List[str]


class BridgeBase(BaseModel):
    id: int
    name: str
    city: str


class BridgeListResponse(BaseModel):
    bridges: List[BridgeBase]


class BridgeMapItem(BaseModel):
    id: int
    name: str
    city: str
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    max_severity: int
    total_cracks: int
    high_severity_cracks: int
    recommendation: str


class BridgeMapResponse(BaseModel):
    bridges: List[BridgeMapItem]


class BridgeStatusResponse(BaseModel):
    bridge_name: str
    city: str
    overall_severity: int
    total_cracks: int
    high_severity_cracks: int
    last_inspection_date: str
    recommendation: str
    current_sensors: Dict[str, Optional[float]]


class InspectionReportBrief(BaseModel):
    id: int
    date: str
    total_cracks: int
    high_severity: int


class BridgeReportsResponse(BaseModel):
    reports: List[InspectionReportBrief]
    total: int
    limit: Optional[int] = None
    offset: int = 0


class ErrorResponse(BaseModel):
    error: str
    detail: Optional[str] = None


class SortOrder(str, Enum):
    asc = "asc"
    desc = "desc"


class ReportSortField(str, Enum):
    date = "date"
    total_cracks = "total_cracks"
    high_severity = "high_severity"


class SensorTimeRange(str, Enum):
    thirty_seconds = "30s"
    one_hour = "1h"
    twenty_four_hours = "24h"


# ─────────────────────────────────────────────────────────────────
# Road distress detection schemas
# ─────────────────────────────────────────────────────────────────

class RoadSegmentCreate(BaseModel):
    segment_name: str = Field(..., min_length=1, max_length=255)
    road_name: Optional[str] = Field(None, max_length=255)
    city: str = Field(..., min_length=1, max_length=100)
    latitude: Optional[float] = None
    longitude: Optional[float] = None


class RoadSegmentBrief(BaseModel):
    id: int
    name: str
    road_name: Optional[str] = None
    city: str


class RoadSegmentListResponse(BaseModel):
    segments: List[RoadSegmentBrief] = Field(default_factory=list)


class RoadSegmentCreateResponse(BaseModel):
    id: int
    name: str
    city: str


class RoadDistressBase(BaseModel):
    x: float = Field(..., ge=0)
    y: float = Field(..., ge=0)
    width: float = Field(..., gt=0)
    height: float = Field(..., gt=0)
    confidence: float = Field(..., ge=0, le=1)
    distress_type: str = Field(..., min_length=1, max_length=100)
    severity: Optional[int] = Field(None, ge=1, le=3)
    near_manhole: bool = False


class RoadDetectResponse(BaseModel):
    distresses: List[RoadDistressBase] = Field(default_factory=list)
    error: Optional[str] = None


class RoadSaveResponse(BaseModel):
    message: Optional[str] = None
    report_id: Optional[int] = None
    pothole_count: Optional[int] = None
    pci_score: Optional[float] = None
    category_en: Optional[str] = None
    category_ar: Optional[str] = None
    total_deducts: Optional[float] = None
    message_en: Optional[str] = None
    message_ar: Optional[str] = None
    error: Optional[str] = None


class RoadPCIResponse(BaseModel):
    segment_name: str
    pci_score: float
    category_en: str
    category_ar: str
    pothole_count: int
    total_distresses: int
    report_date: str
    message_en: str
    message_ar: str


class RoadMapItem(BaseModel):
    id: int
    name: str
    road_name: Optional[str] = None
    city: str
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    pci_score: Optional[float] = None
    pci_category: Optional[str] = None
    pothole_count: int = 0
    total_distresses: int = 0


class RoadMapResponse(BaseModel):
    segments: List[RoadMapItem] = Field(default_factory=list)

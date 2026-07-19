from database import SessionLocal, init_db
from models import Bridge, CrackDetection, SensorData, InspectionReport, RoadSegment, RoadDistressDetection, RoadInspectionReport
from crack_linking import generate_crack_identifier
from pci_scoring import compute_pci
from datetime import datetime, timedelta

# ─────────────────────────────────────────────
# Cairo road segments with real GIS coordinates
# ─────────────────────────────────────────────
CAIRO_ROAD_SEGMENTS = [
    {"name": "Salah Salem Rd — Nasr City stretch", "road": "Salah Salem", "city": "Cairo", "lat": 30.0658, "lng": 31.3242},
    {"name": "Corniche El-Nil — Maadi stretch",     "road": "Corniche El-Nil", "city": "Cairo", "lat": 29.9602, "lng": 31.2569},
    {"name": "Ring Road — 6th October section",     "road": "Ring Road", "city": "Giza", "lat": 29.9997, "lng": 31.0122},
]

# ─────────────────────────────────────────────
# Cairo bridges with real GIS coordinates
# ─────────────────────────────────────────────
CAIRO_BRIDGES = [
    {"name": "Qasr El-Nile Bridge",  "city": "Cairo", "lat": 30.0459, "lng": 31.2243},
    {"name": "6th October Bridge",   "city": "Cairo", "lat": 30.0571, "lng": 31.2272},
    {"name": "Imbaba Bridge",        "city": "Cairo", "lat": 30.0771, "lng": 31.2089},
]

def init_mock_data():
    db = SessionLocal()
    try:
        # ── 1. Create all three Cairo bridges ──────────────────────────────
        bridge_objs = []
        for b in CAIRO_BRIDGES:
            bridge = Bridge(
                bridge_name=b["name"],
                city=b["city"],
                inspection_date=datetime.utcnow(),
                latitude=b["lat"],
                longitude=b["lng"],
            )
            db.add(bridge)
        db.commit()

        # Re-fetch to get IDs
        from models import Bridge as BridgeModel
        bridge_objs = db.query(BridgeModel).all()
        primary_bridge = bridge_objs[0]  # Qasr El-Nile — used for rich seed data

        # ── 2. Sensor history for primary bridge ───────────────────────────
        for i in range(7):
            db.add(SensorData(
                bridge_id=primary_bridge.id,
                temperature_c=32 + i,
                moisture_percent=45 + i,
                acceleration_x=0.8 + (i * 0.01),
                strain_gauge_value=120 + i,
                timestamp=datetime.utcnow() - timedelta(days=6 - i)
            ))

        # ── 3. Generic cracks for primary bridge ───────────────────────────
        for i in range(12):
            x = 100 + i * 50
            y = 100 + i * 30
            db.add(CrackDetection(
                bridge_id=primary_bridge.id,
                x=x,
                y=y,
                width=50 + i * 10,
                height=20 + i * 5,
                area=(50 + i * 10) * (20 + i * 5),
                confidence=0.6 + i * 0.03,
                severity_level=1 if i < 7 else 2 if i < 10 else 3,
                crack_type="hairline" if i < 10 else "structural",
                crack_identifier=generate_crack_identifier(x, y),
            ))

        db.commit()

        # ── 4. Crack-lineage seed data (Feature 1 demo) ────────────────────
        # Three backdated inspections of the same physical crack, growing over 21 days.
        LINEAGE_ID = "CRK-CAIRO12-001"

        detection_1 = CrackDetection(
            bridge_id=primary_bridge.id,
            x=300, y=200,
            width=60,  height=25,  area=1500,
            confidence=0.72, severity_level=1,
            crack_type="hairline",
            crack_identifier=LINEAGE_ID,
            previous_crack_id=None,
            detected_at=datetime.utcnow() - timedelta(days=21),
        )
        db.add(detection_1)
        db.flush()  # get detection_1.id

        detection_2 = CrackDetection(
            bridge_id=primary_bridge.id,
            x=302, y=201,
            width=90,  height=38,  area=3420,
            confidence=0.81, severity_level=2,
            crack_type="hairline",
            crack_identifier=LINEAGE_ID,
            previous_crack_id=detection_1.id,
            detected_at=datetime.utcnow() - timedelta(days=10),
        )
        db.add(detection_2)
        db.flush()

        detection_3 = CrackDetection(
            bridge_id=primary_bridge.id,
            x=304, y=200,
            width=130, height=62,  area=8060,
            confidence=0.91, severity_level=3,
            crack_type="structural",
            crack_identifier=LINEAGE_ID,
            previous_crack_id=detection_2.id,
            detected_at=datetime.utcnow(),
        )
        db.add(detection_3)

        # ── 5. Cracks for 6th October Bridge (severity 2) ──────────────────
        bridge2 = bridge_objs[1]
        for i in range(5):
            db.add(CrackDetection(
                bridge_id=bridge2.id,
                x=200 + i * 40, y=150 + i * 20,
                width=40 + i * 8, height=18 + i * 4, area=(40 + i * 8) * (18 + i * 4),
                confidence=0.70 + i * 0.04, severity_level=2,
                crack_type="hairline",
                crack_identifier=f"CRK-OCT-00{i+1}",
            ))

        # ── 6. Minor cracks for Imbaba Bridge (severity 1) ─────────────────
        bridge3 = bridge_objs[2]
        for i in range(3):
            db.add(CrackDetection(
                bridge_id=bridge3.id,
                x=100 + i * 60, y=80 + i * 30,
                width=30 + i * 5, height=12 + i * 3, area=(30 + i * 5) * (12 + i * 3),
                confidence=0.65 + i * 0.03, severity_level=1,
                crack_type="hairline",
                crack_identifier=f"CRK-IMB-00{i+1}",
            ))

        # ── 7. Inspection report ───────────────────────────────────────────
        db.add(InspectionReport(
            bridge_id=primary_bridge.id,
            report_date=datetime.utcnow(),
            total_cracks_detected=15,
            high_severity_cracks=2,
            status="Completed",
        ))

        db.commit()
        print("✅ Mock data (including crack lineage + bridge coordinates) added successfully!")

        # ── 8. Admin user seed (for demo — first Google login can be promoted) ──
        from models import User, SensorDevice, SystemSetting
        admin = db.query(User).filter(User.role == "Admin").first()
        if not admin:
            admin = User(
                google_id="admin-seed-demo",
                full_name="System Admin",
                email="admin@bridge-crack.local",
                role="Admin",
                is_active=True,
            )
            db.add(admin)

        for bridge in bridge_objs:
            device_id = f"bridge_{bridge.id}_sensor"
            if not db.query(SensorDevice).filter(SensorDevice.device_id == device_id).first():
                db.add(SensorDevice(
                    bridge_id=bridge.id,
                    device_id=device_id,
                    mqtt_topic=f"sensors/bridge_{bridge.id}/data",
                    status="disconnected",
                ))

        if not db.query(SystemSetting).filter(SystemSetting.key == "retrain_threshold").first():
            db.add(SystemSetting(key="retrain_threshold", value="100"))

        db.commit()
        print("✅ Admin seed data (admin user, sensors, settings) added!")
    except Exception as e:
        db.rollback()
        print(f"Error adding mock data: {e}")
    finally:
        db.close()

def init_road_mock_data():
    db = SessionLocal()
    try:
        for r in CAIRO_ROAD_SEGMENTS:
            if db.query(RoadSegment).filter(RoadSegment.segment_name == r["name"]).first():
                continue
            db.add(RoadSegment(
                segment_name=r["name"],
                road_name=r["road"],
                city=r["city"],
                inspection_date=datetime.utcnow(),
                latitude=r["lat"],
                longitude=r["lng"],
            ))
        db.commit()

        segments = db.query(RoadSegment).all()

        # width/height in px, matching the scale services/roads.py's
        # classify_road_severity() expects (see constants.py thresholds)
        SEED_DISTRESS_SETS = [
            [
                {"x": 300, "y": 200, "width": 90, "height": 70, "distress_type": "pothole", "severity": 2, "near_manhole": False},
                {"x": 500, "y": 210, "width": 60, "height": 50, "distress_type": "pothole", "severity": 1, "near_manhole": False},
                {"x": 150, "y": 300, "width": 220, "height": 20, "distress_type": "longitudinal_crack", "severity": 3, "near_manhole": False},
            ],
            [
                {"x": 400, "y": 150, "width": 60, "height": 15, "distress_type": "transverse_crack", "severity": 1, "near_manhole": False},
            ],
            [
                {"x": 250, "y": 250, "width": 130, "height": 110, "distress_type": "alligator_crack", "severity": 3, "near_manhole": True},
                {"x": 260, "y": 260, "width": 30, "height": 30, "distress_type": "manhole", "severity": None, "near_manhole": False},
                {"x": 450, "y": 300, "width": 95, "height": 85, "distress_type": "pothole", "severity": 2, "near_manhole": False},
                {"x": 600, "y": 320, "width": 100, "height": 90, "distress_type": "pothole", "severity": 3, "near_manhole": False},
            ],
        ]

        for segment, distresses in zip(segments, SEED_DISTRESS_SETS):
            if db.query(RoadInspectionReport).filter(RoadInspectionReport.segment_id == segment.id).first():
                continue  # already seeded

            pothole_count = len([d for d in distresses if d["distress_type"] == "pothole"])
            report = RoadInspectionReport(
                segment_id=segment.id,
                report_date=datetime.utcnow(),
                total_distresses_detected=len(distresses),
                pothole_count=pothole_count,
                status="Pending",
            )
            db.add(report)
            db.flush()

            for d in distresses:
                db.add(RoadDistressDetection(
                    segment_id=segment.id,
                    report_id=report.id,
                    x=d["x"], y=d["y"], width=d["width"], height=d["height"],
                    area=d["width"] * d["height"],
                    confidence=0.85,
                    distress_type=d["distress_type"],
                    severity_level=d["severity"],
                    near_manhole=bool(d["near_manhole"]),
                ))

            pci = compute_pci([
                {"distress_type": d["distress_type"], "severity_level": d["severity"], "near_manhole": d["near_manhole"]}
                for d in distresses
            ])
            report.pci_score = pci["pci_score"]
            report.pci_category = pci["category_en"]

        db.commit()
        print("✅ Road segment mock data (with seeded distresses + PCI scores) added!")
    except Exception as e:
        db.rollback()
        print(f"Error adding road mock data: {e}")
    finally:
        db.close()


if __name__ == "__main__":
    init_db()  # Create database tables first
    init_mock_data()
    init_road_mock_data()


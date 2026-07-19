import React, { useState, useEffect } from 'react';
import { authenticatedFetch, API_URL } from '../api';
import RoadMap from './RoadMap';

const DISTRESS_LABELS = {
  en: {
    longitudinal_crack: 'Longitudinal Crack',
    transverse_crack: 'Transverse Crack',
    alligator_crack: 'Alligator Crack',
    pothole: 'Pothole',
    manhole: 'Manhole',
  },
  ar: {
    longitudinal_crack: 'شرخ طولي',
    transverse_crack: 'شرخ عرضي',
    alligator_crack: 'شرخ تمساحي',
    pothole: 'حفرة',
    manhole: 'غطاء بالوعة',
  },
};

const SEVERITY_LABELS = {
  en: { 1: 'Low', 2: 'Medium', 3: 'High' },
  ar: { 1: 'منخفضة', 2: 'متوسطة', 3: 'عالية' },
};

export default function RoadDetection({ language }) {
  const [view, setView] = useState('detect'); // 'detect' | 'map'

  const [segments, setSegments] = useState([]);
  const [segmentId, setSegmentId] = useState(null);
  const [showAddSegment, setShowAddSegment] = useState(false);
  const [newSegment, setNewSegment] = useState({ segment_name: '', road_name: '', city: '', latitude: '', longitude: '' });
  const [addingSegment, setAddingSegment] = useState(false);

  const [selectedImage, setSelectedImage] = useState(null);
  const [distresses, setDistresses] = useState([]);
  const [loading, setLoading] = useState(false);
  const [saving, setSaving] = useState(false);
  const [detectionAttempted, setDetectionAttempted] = useState(false);
  const [pci, setPci] = useState(null);

  const isRtl = language === 'ar';

  const t = {
    en: {
      title: 'Road Distress Detection',
      mapView: 'Network Map',
      detectView: 'Detect',
      selectSegment: 'Select Road Segment',
      addSegment: '+ Add Segment',
      segmentName: 'Segment name',
      roadName: 'Road name (optional)',
      city: 'City',
      latitude: 'Latitude (optional)',
      longitude: 'Longitude (optional)',
      cancel: 'Cancel',
      save: 'Save Segment',
      noSegments: 'No road segments yet — add one to get started.',
      uploadPhoto: 'Upload Photo',
      selectImage: 'Select Image from Device',
      detect: 'Detect Distresses',
      noImage: 'No image selected',
      loading: 'Analyzing image...',
      distressCount: 'Distresses Found',
      confidence: 'Confidence',
      severity: 'Severity',
      nearManhole: '⚠ Near manhole',
      saveDetections: 'Save Detections',
      saving: 'Saving...',
      savedSuccessfully: 'Detections saved successfully!',
      noDistressDetected: 'No road distress detected in this image.',
      pciTitle: 'Segment Condition (PCI)',
      potholeCount: 'Pothole Count',
      pleaseSelect: 'Select a road segment above to begin.',
    },
    ar: {
      title: 'كشف أضرار الطرق',
      mapView: 'خريطة الشبكة',
      detectView: 'الكشف',
      selectSegment: 'اختر قطعة الطريق',
      addSegment: '+ إضافة قطعة',
      segmentName: 'اسم القطعة',
      roadName: 'اسم الطريق (اختياري)',
      city: 'المدينة',
      latitude: 'خط العرض (اختياري)',
      longitude: 'خط الطول (اختياري)',
      cancel: 'إلغاء',
      save: 'حفظ القطعة',
      noSegments: 'لا توجد قطع طرق بعد — أضف واحدة للبدء.',
      uploadPhoto: 'تحميل صورة',
      selectImage: 'اختر صورة من الجهاز',
      detect: 'كشف الأضرار',
      noImage: 'لم يتم اختيار صورة',
      loading: 'جاري تحليل الصورة...',
      distressCount: 'الأضرار المكتشفة',
      confidence: 'الثقة',
      severity: 'الشدة',
      nearManhole: '⚠ بالقرب من بالوعة',
      saveDetections: 'حفظ الكشوفات',
      saving: 'جاري الحفظ...',
      savedSuccessfully: 'تم حفظ الكشوفات بنجاح!',
      noDistressDetected: 'لم يتم اكتشاف أي أضرار في هذه الصورة.',
      pciTitle: 'حالة القطعة (PCI)',
      potholeCount: 'عدد الحفر',
      pleaseSelect: 'اختر قطعة طريق أعلاه للبدء.',
    },
  }[language];

  useEffect(() => {
    fetchSegments();
  }, []);

  const fetchSegments = async () => {
    try {
      const res = await authenticatedFetch(`${API_URL}/road-segments`);
      const data = await res.json();
      const list = data.segments || [];
      setSegments(list);
      if (list.length > 0 && !segmentId) setSegmentId(list[0].id);
    } catch (err) {
      console.error('Failed to fetch road segments:', err);
    }
  };

  const handleAddSegment = async () => {
    if (!newSegment.segment_name || !newSegment.city) return;
    setAddingSegment(true);
    try {
      const res = await authenticatedFetch(`${API_URL}/road-segments`, {
        method: 'POST',
        body: JSON.stringify({
          segment_name: newSegment.segment_name,
          road_name: newSegment.road_name || null,
          city: newSegment.city,
          latitude: newSegment.latitude ? parseFloat(newSegment.latitude) : null,
          longitude: newSegment.longitude ? parseFloat(newSegment.longitude) : null,
        }),
      });
      const data = await res.json();
      setNewSegment({ segment_name: '', road_name: '', city: '', latitude: '', longitude: '' });
      setShowAddSegment(false);
      await fetchSegments();
      setSegmentId(data.id);
    } catch (err) {
      console.error('Failed to add road segment:', err);
      alert('Error adding road segment');
    }
    setAddingSegment(false);
  };

  const handleImageSelect = (e) => {
    const file = e.target.files[0];
    if (file) {
      const reader = new FileReader();
      reader.onload = (event) => {
        setSelectedImage(event.target.result);
        setDistresses([]);
        setDetectionAttempted(false);
        setPci(null);
      };
      reader.readAsDataURL(file);
    }
  };

  const handleDetect = async () => {
    if (!selectedImage) return;
    setLoading(true);
    setDetectionAttempted(true);

    try {
      const blob = await (await fetch(selectedImage)).blob();
      const formData = new FormData();
      formData.append('image', blob, 'image.jpg');

      const response = await authenticatedFetch(`${API_URL}/road-detect`, {
        method: 'POST',
        body: formData,
      });
      const data = await response.json();

      const formatted = (data.distresses || []).map((d, i) => ({
        id: i + 1,
        x: Math.round(d.x),
        y: Math.round(d.y),
        width: Math.round(d.width),
        height: Math.round(d.height),
        confidence: d.confidence,
        distress_type: d.distress_type,
        severity: d.severity,
        near_manhole: d.near_manhole,
      }));

      setDistresses(formatted);
    } catch (err) {
      console.error('Road detection error:', err);
      alert('Error detecting road distress. Is backend running?');
    }
    setLoading(false);
  };

  const handleSave = async () => {
    if (!segmentId || distresses.length === 0) return;
    setSaving(true);
    try {
      const response = await authenticatedFetch(`${API_URL}/road-detect/${segmentId}/save`, {
        method: 'POST',
        body: JSON.stringify(distresses),
      });
      const data = await response.json();
      if (data.error) {
        alert(data.error);
      } else {
        alert(t.savedSuccessfully);
        setPci(data); // save response already includes pci_score/category/message
        setDistresses([]);
        setSelectedImage(null);
      }
    } catch (err) {
      console.error('Save error:', err);
      alert('Error saving detections');
    }
    setSaving(false);
  };

  const getDistressLabel = (type) => DISTRESS_LABELS[language]?.[type] || type;
  const getSeverityLabel = (level) => (level ? SEVERITY_LABELS[language]?.[level] : '—');

  return (
    <div className="crack-detection" dir={isRtl ? 'rtl' : 'ltr'}>
      {/* Detect / Map toggle */}
      <div style={{ display: 'flex', gap: 8, padding: '0 0 12px' }}>
        <button
          className={`btn-small ${view === 'detect' ? 'active' : ''}`}
          onClick={() => setView('detect')}
        >
          🔍 {t.detectView}
        </button>
        <button
          className={`btn-small ${view === 'map' ? 'active' : ''}`}
          onClick={() => setView('map')}
        >
          🛣️ {t.mapView}
        </button>
      </div>

      {view === 'map' ? (
        <RoadMap language={language} />
      ) : (
        <>
          {/* Segment selector */}
          <div className="card">
            <div className="card-header">{t.selectSegment}</div>
            <div style={{ padding: '12px 16px', display: 'flex', flexDirection: 'column', gap: 10 }}>
              {segments.length > 0 ? (
                <select
                  value={segmentId || ''}
                  onChange={(e) => { setSegmentId(parseInt(e.target.value)); setPci(null); }}
                >
                  {segments.map((s) => (
                    <option key={s.id} value={s.id}>
                      {s.name}{s.road_name ? ` (${s.road_name})` : ''} — {s.city}
                    </option>
                  ))}
                </select>
              ) : (
                <p style={{ color: '#718096', margin: 0 }}>{t.noSegments}</p>
              )}

              {!showAddSegment ? (
                <button className="btn-small secondary" onClick={() => setShowAddSegment(true)}>
                  {t.addSegment}
                </button>
              ) : (
                <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
                  <input
                    type="text" placeholder={t.segmentName}
                    value={newSegment.segment_name}
                    onChange={(e) => setNewSegment({ ...newSegment, segment_name: e.target.value })}
                  />
                  <input
                    type="text" placeholder={t.roadName}
                    value={newSegment.road_name}
                    onChange={(e) => setNewSegment({ ...newSegment, road_name: e.target.value })}
                  />
                  <input
                    type="text" placeholder={t.city}
                    value={newSegment.city}
                    onChange={(e) => setNewSegment({ ...newSegment, city: e.target.value })}
                  />
                  <div style={{ display: 'flex', gap: 8 }}>
                    <input
                      type="text" placeholder={t.latitude}
                      value={newSegment.latitude}
                      onChange={(e) => setNewSegment({ ...newSegment, latitude: e.target.value })}
                    />
                    <input
                      type="text" placeholder={t.longitude}
                      value={newSegment.longitude}
                      onChange={(e) => setNewSegment({ ...newSegment, longitude: e.target.value })}
                    />
                  </div>
                  <div style={{ display: 'flex', gap: 8 }}>
                    <button className="btn-primary" onClick={handleAddSegment} disabled={addingSegment}>
                      {addingSegment ? t.saving : t.save}
                    </button>
                    <button className="btn-small secondary" onClick={() => setShowAddSegment(false)}>
                      {t.cancel}
                    </button>
                  </div>
                </div>
              )}
            </div>
          </div>

          {!segmentId ? (
            <div className="card"><p style={{ padding: 16, color: '#718096' }}>{t.pleaseSelect}</p></div>
          ) : (
            <>
              {/* Upload section */}
              <div className="upload-section">
                <div className="card">
                  <div className="card-header">{t.uploadPhoto}</div>
                  <div className="upload-controls">
                    <label htmlFor="road-image-input" className="upload-btn primary">
                      📁 {t.selectImage}
                    </label>
                    <input
                      id="road-image-input"
                      type="file"
                      accept="image/*"
                      onChange={handleImageSelect}
                      style={{ display: 'none' }}
                    />
                  </div>

                  {selectedImage && (
                    <div className="image-preview">
                      <img src={selectedImage} alt="Preview" />
                      <button className="btn-primary" onClick={handleDetect} disabled={loading}>
                        {loading ? t.loading : t.detect}
                      </button>
                    </div>
                  )}

                  {!selectedImage && (
                    <div className="no-image">
                      <p>📸 {t.noImage}</p>
                    </div>
                  )}
                </div>
              </div>

              {detectionAttempted && !loading && distresses.length === 0 && (
                <div className="results-section">
                  <div className="card">
                    <div className="card-header" style={{ color: '#ff6b6b' }}>⚠️ Detection Result</div>
                    <div style={{ padding: '20px', textAlign: 'center', color: '#4a5568' }}>
                      <p>{t.noDistressDetected}</p>
                    </div>
                  </div>
                </div>
              )}

              {distresses.length > 0 && (
                <div className="results-section">
                  <div className="card">
                    <div className="card-header" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                      <span>{t.distressCount}: {distresses.length}</span>
                      <button className="btn-primary" onClick={handleSave} disabled={saving}>
                        {saving ? t.saving : t.saveDetections}
                      </button>
                    </div>

                    <div className="crack-list">
                      {distresses.map((d) => (
                        <div key={d.id} className="crack-item">
                          <div className="crack-header">
                            <span className="crack-type">{getDistressLabel(d.distress_type)}</span>
                            {d.severity && (
                              <span className={`severity-badge severity-${d.severity}`}>
                                {getSeverityLabel(d.severity)}
                              </span>
                            )}
                          </div>

                          <div className="crack-metrics">
                            <div className="metric">
                              <span className="metric-label">{t.confidence}</span>
                              <div className="progress-bar">
                                <div className="progress-fill" style={{ width: `${d.confidence * 100}%` }}></div>
                              </div>
                              <span className="metric-value">{(d.confidence * 100).toFixed(0)}%</span>
                            </div>
                          </div>

                          {d.near_manhole && (
                            <div style={{ marginTop: 6, fontSize: '0.8rem', color: '#dd6b20', fontWeight: 600 }}>
                              {t.nearManhole}
                            </div>
                          )}
                        </div>
                      ))}
                    </div>
                  </div>
                </div>
              )}

              {loading && (
                <div className="loading-indicator">
                  <div className="spinner"></div>
                  <p>{t.loading}</p>
                </div>
              )}

              {/* PCI result card, shown right after a successful save */}
              {pci && (
                <div className="card" style={{ marginTop: 12 }}>
                  <div className="card-header">📊 {t.pciTitle}</div>
                  <div style={{ padding: '14px 16px' }}>
                    <div style={{ fontSize: '2rem', fontWeight: 700 }}>
                      {pci.pci_score}
                      <span style={{ fontSize: '1rem', fontWeight: 500, color: '#718096', marginLeft: 8 }}>
                        {language === 'ar' ? pci.category_ar : pci.category_en}
                      </span>
                    </div>
                    <div style={{ marginTop: 6, color: '#4a5568', fontSize: '0.85rem' }}>
                      🕳️ {t.potholeCount}: {pci.pothole_count}
                    </div>
                  </div>
                </div>
              )}
            </>
          )}
        </>
      )}
    </div>
  );
}

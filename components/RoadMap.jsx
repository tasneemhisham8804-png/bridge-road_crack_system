
import React, { useState, useEffect } from 'react';
import { MapContainer, TileLayer, CircleMarker, Popup } from 'react-leaflet';
import 'leaflet/dist/leaflet.css';
import { authenticatedFetch, API_URL } from '../api';

// PCI category → colour mapping using the existing CSS variable palette
const CATEGORY_COLORS = {
  Good: '#38a169',
  Satisfactory: '#68a06a',
  Fair: '#dd6b20',
  Poor: '#e07b39',
  'Very Poor': '#e53e3e',
  Failed: '#9b2c2c',
};
const NO_DATA_COLOR = '#a0aec0';

const CATEGORY_LABELS = {
  en: {
    Good: 'Good', Satisfactory: 'Satisfactory', Fair: 'Fair',
    Poor: 'Poor', 'Very Poor': 'Very Poor', Failed: 'Failed',
  },
  ar: {
    Good: 'جيدة', Satisfactory: 'مقبولة', Fair: 'متوسطة',
    Poor: 'سيئة', 'Very Poor': 'سيئة جداً', Failed: 'فاشلة',
  },
};

export default function RoadMap({ language }) {
  const [segments, setSegments] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const isRtl = language === 'ar';

  const t = {
    en: {
      title: 'Road Network Map',
      subtitle: 'All segments colored by PCI condition',
      pci: 'PCI Score',
      potholes: 'Potholes',
      distresses: 'Distresses',
      noData: 'Not inspected yet',
      loading: 'Loading map data…',
    },
    ar: {
      title: 'خريطة شبكة الطرق',
      subtitle: 'جميع القطع ملونة حسب حالة الرصف',
      pci: 'مؤشر حالة الرصف',
      potholes: 'الحفر',
      distresses: 'الأضرار',
      noData: 'لم يتم الفحص بعد',
      loading: 'جاري تحميل بيانات الخريطة…',
    },
  }[language] || {
    title: 'Road Network Map', subtitle: 'All segments colored by PCI condition',
    pci: 'PCI Score', potholes: 'Potholes', distresses: 'Distresses',
    noData: 'Not inspected yet', loading: 'Loading map data…',
  };

  useEffect(() => {
    authenticatedFetch(`${API_URL}/road-segments/map`)
      .then(r => r.json())
      .then(data => {
        setSegments(data.segments || []);
        setLoading(false);
      })
      .catch(err => {
        setError(err.message);
        setLoading(false);
      });
  }, []);

  if (loading) {
    return (
      <div className="bridge-map-page" style={{ display: 'flex', justifyContent: 'center', padding: '40px' }}>
        <div className="spinner" />
        <p style={{ marginLeft: 12 }}>{t.loading}</p>
      </div>
    );
  }

  if (error) {
    return <div style={{ padding: 20, color: '#e53e3e' }}>⚠️ {error}</div>;
  }

  const mapCenter = [30.03, 31.21];

  return (
    <div className="bridge-map-page" dir={isRtl ? 'rtl' : 'ltr'}>
      <div className="card" style={{ marginBottom: 0 }}>
        <div className="card-header">
          🛣️ {t.title}
          <span style={{ fontSize: '0.78rem', fontWeight: 400, color: '#718096', marginLeft: 8 }}>
            {t.subtitle}
          </span>
        </div>

        <div style={{ display: 'flex', gap: 12, padding: '8px 16px', flexWrap: 'wrap' }}>
          {Object.keys(CATEGORY_COLORS).map(cat => (
            <span key={cat} style={{ display: 'flex', alignItems: 'center', gap: 6, fontSize: '0.78rem' }}>
              <span style={{
                width: 12, height: 12, borderRadius: '50%',
                background: CATEGORY_COLORS[cat], display: 'inline-block',
              }} />
              {CATEGORY_LABELS[language]?.[cat] || cat}
            </span>
          ))}
        </div>
      </div>

      <div style={{ height: 380, borderRadius: '0 0 12px 12px', overflow: 'hidden' }}>
        <MapContainer
          center={mapCenter}
          zoom={11}
          style={{ height: '100%', width: '100%' }}
          scrollWheelZoom={false}
        >
          <TileLayer
            attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>'
            url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
          />

          {segments
            .filter(s => s.latitude && s.longitude)
            .map(segment => {
              const color = segment.pci_category
                ? (CATEGORY_COLORS[segment.pci_category] || NO_DATA_COLOR)
                : NO_DATA_COLOR;
              const catLabel = segment.pci_category
                ? (CATEGORY_LABELS[language]?.[segment.pci_category] || segment.pci_category)
                : t.noData;

              return (
                <CircleMarker
                  key={segment.id}
                  center={[segment.latitude, segment.longitude]}
                  radius={16}
                  pathOptions={{ color, fillColor: color, fillOpacity: 0.75, weight: 2 }}
                >
                  <Popup>
                    <div style={{ minWidth: 170, fontFamily: 'inherit', fontSize: '0.85rem' }}>
                      <strong style={{ fontSize: '0.95rem', display: 'block', marginBottom: 4 }}>
                        {segment.name}
                      </strong>
                      {segment.road_name && <div>🛣️ {segment.road_name}</div>}
                      <div>📍 {segment.city}</div>
                      <div>
                        <span style={{
                          display: 'inline-block', marginTop: 6, padding: '2px 8px',
                          borderRadius: 10, fontSize: '0.78rem', fontWeight: 700,
                          background: color + '25', color,
                        }}>
                          {segment.pci_score !== null ? `${t.pci}: ${segment.pci_score} — ${catLabel}` : catLabel}
                        </span>
                      </div>
                      {segment.pci_score !== null && (
                        <div style={{ marginTop: 6, color: '#4a5568' }}>
                          🕳️ {t.potholes}: {segment.pothole_count}<br />
                          ⚠️ {t.distresses}: {segment.total_distresses}
                        </div>
                      )}
                    </div>
                  </Popup>
                </CircleMarker>
              );
            })}
        </MapContainer>
      </div>

      <div style={{ marginTop: 12, display: 'flex', flexDirection: 'column', gap: 8 }}>
        {segments.map(segment => {
          const color = segment.pci_category
            ? (CATEGORY_COLORS[segment.pci_category] || NO_DATA_COLOR)
            : NO_DATA_COLOR;
          const catLabel = segment.pci_category
            ? (CATEGORY_LABELS[language]?.[segment.pci_category] || segment.pci_category)
            : t.noData;
          return (
            <div
              key={segment.id}
              className="card"
              style={{ borderLeft: `4px solid ${color}`, margin: 0, padding: '10px 14px' }}
            >
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <strong style={{ fontSize: '0.9rem' }}>{segment.name}</strong>
                <span style={{
                  padding: '2px 10px', borderRadius: 10, fontSize: '0.78rem',
                  fontWeight: 700, background: color + '20', color,
                }}>
                  {segment.pci_score !== null ? `${segment.pci_score} · ${catLabel}` : catLabel}
                </span>
              </div>
              {segment.pci_score !== null && (
                <div style={{ fontSize: '0.8rem', color: '#718096', marginTop: 2 }}>
                  🕳️ {segment.pothole_count} {t.potholes} · ⚠️ {segment.total_distresses} {t.distresses}
                </div>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
}

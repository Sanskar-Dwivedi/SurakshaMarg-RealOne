import React, { useState, useEffect } from 'react';
import { Sidebar, ViewId } from './Sidebar';
import { Header } from './Header';
import { OverviewDashboard } from '../views/OverviewDashboard';
import { LiveMonitorView } from '../views/LiveMonitorView';
import { IncidentsView } from '../views/IncidentsView';
import { IncidentDetailView } from '../views/IncidentDetailView';
import { AnalyticsView } from '../views/AnalyticsView';
import { CameraNetworkView } from '../views/CameraNetworkView';
import { SettingsView } from '../views/SettingsView';
import { Modal } from '../common/Modal';
import { useGauKavachStream, BackendCamera } from '../../hooks/useGauKavachStream';
import { EvidenceEnvelope } from '../../data/mockData';

export const AppShell: React.FC = () => {
  const [currentView, setCurrentView] = useState<ViewId>('overview');
  const [selectedEnvelope, setSelectedEnvelope] = useState<EvidenceEnvelope | null>(null);

  // Real-time backend stream & telemetry hook
  const {
    connectionStatus,
    telemetry,
    camera,
    fps,
    latencyMs,
    animalCount,
    detections,
    incidents,
    ledgerValid,
    takeSnapshot,
    streamUrl,
    getStreamUrl,
  } = useGauKavachStream('ws://localhost:8000/ws', 'http://localhost:8000');

  const [availableCameras, setAvailableCameras] = useState<BackendCamera[]>([camera]);
  const [activeCamera, setActiveCamera] = useState<BackendCamera>(camera);

  useEffect(() => {
    fetch('http://localhost:8000/api/cameras')
      .then(res => res.json())
      .then(cams => {
        if (Array.isArray(cams) && cams.length > 0) {
          setAvailableCameras(cams);
          setActiveCamera(cams[0]);
        }
      })
      .catch(() => {
        // Fallback if backend offline
      });
  }, []);

  useEffect(() => {
    if (camera && camera.id) {
      setActiveCamera(prev => ({ ...prev, ...camera }));
    }
  }, [camera]);

  const handleReviewIncident = (incidentNo: string) => {
    const foundIncident = incidents.find(i => i.incidentNo === incidentNo);
    const mockEnvelope: EvidenceEnvelope = {
      id: foundIncident?.id || 'EV-0248',
      incidentNo: incidentNo,
      timestamp: foundIncident?.timestamp || '15:44:12 IST',
      cameraId: foundIncident?.cameraId || activeCamera.id,
      cameraName: foundIncident?.cameraName || activeCamera.name,
      location: foundIncident?.location || activeCamera.location,
      sector: foundIncident?.sector || activeCamera.sector,
      animalType: foundIncident?.species || 'Cattle (Bovine)',
      count: 1,
      confidence: foundIncident?.confidence || 94.8,
      severity: (foundIncident?.severity as any) || 'high_risk',
      status: 'Open',
      frameImage: streamUrl,
      videoDurationSec: 15,
      speedLimitKmh: 80,
      estRoadOccupancySec: 140,
      weatherCondition: 'Clear · Day Vision',
      lightCondition: 'Daylight (Sun angle 42°)',
      operatorNotes: 'Cattle detected on road shoulder. High collision risk for fast lane traffic.',
      auditTrail: [
        { time: '15:18:42', action: 'System Detection', actor: 'GauVision YOLO Engine', notes: 'Automated bounding box trigger.' },
        { time: '15:19:05', action: 'Alert Raised', actor: 'Central Dispatch System', notes: 'Dispatched notification to Control Room.' },
      ]
    };
    setSelectedEnvelope(mockEnvelope);
  };

  const mappedAlerts = incidents.map(i => ({
    id: i.id,
    incidentNo: i.incidentNo,
    timeAgo: i.timestamp,
    timestamp: i.timestamp,
    title: `Animal Detected in ${i.sector}`,
    location: i.location,
    sector: i.sector,
    animalType: i.species,
    distanceToCarriagewayMeters: 1.5,
    severity: i.severity === 'high_risk' ? ('critical' as const) : ('attention' as const),
    recommendedAction: i.actionTaken,
    status: i.status,
    cameraId: i.cameraId,
  }));

  return (
    <div className="flex min-h-screen bg-cream font-sans text-charcoal antialiased">
      {/* 240px Sidebar Navigation Rail */}
      <Sidebar
        currentView={currentView}
        onNavigate={setCurrentView}
        activeAlertCount={incidents.length}
      />

      {/* Main Administrative Container */}
      <div className="flex-1 flex flex-col min-w-0">
        <Header
          currentView={currentView}
          onOpenNotifications={() => setCurrentView('incidents')}
        />

        <main className="flex-1 p-6 md:p-8 max-w-[1600px] w-full mx-auto relative z-0">
          {currentView === 'overview' && (
            <OverviewDashboard
              cameras={availableCameras}
              selectedCamera={activeCamera}
              onSelectCamera={setActiveCamera}
              detections={detections}
              incidents={incidents}
              fps={fps}
              latencyMs={latencyMs}
              status={connectionStatus}
              animalCount={animalCount}
              takeSnapshot={takeSnapshot}
              streamUrl={streamUrl}
              onReviewIncident={handleReviewIncident}
            />
          )}

          {currentView === 'live-monitor' && (
            <LiveMonitorView
              cameras={availableCameras}
              selectedCamera={activeCamera}
              onSelectCamera={setActiveCamera}
              detections={detections}
              fps={fps}
              latencyMs={latencyMs}
              status={connectionStatus}
              takeSnapshot={takeSnapshot}
              streamUrl={streamUrl}
              getStreamUrl={getStreamUrl}
              onReviewIncident={handleReviewIncident}
            />
          )}

          {currentView === 'incidents' && (
            <IncidentsView
              alerts={mappedAlerts}
              envelopes={[]}
              onReviewIncident={handleReviewIncident}
            />
          )}

          {currentView === 'analytics' && (
            <AnalyticsView />
          )}

          {currentView === 'camera-network' && (
            <CameraNetworkView
              cameras={availableCameras as any}
              onSelectCamera={(cam: any) => {
                setActiveCamera(cam);
                setCurrentView('overview');
              }}
            />
          )}

          {currentView === 'settings' && (
            <SettingsView />
          )}
        </main>
      </div>

      {/* Evidence Envelope & Incident Detail Modal */}
      {selectedEnvelope && (
        <Modal
          isOpen={!!selectedEnvelope}
          onClose={() => setSelectedEnvelope(null)}
          title={`Incident Inspection — #${selectedEnvelope.incidentNo}`}
          subtitle={`${selectedEnvelope.cameraName} · ${selectedEnvelope.location}`}
          maxWidth="4xl"
        >
          <IncidentDetailView
            envelope={selectedEnvelope}
            onClose={() => setSelectedEnvelope(null)}
            onUpdateStatus={() => {}}
          />
        </Modal>
      )}
    </div>
  );
};

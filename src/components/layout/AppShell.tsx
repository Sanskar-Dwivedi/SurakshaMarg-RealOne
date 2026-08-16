import React, { useState } from 'react';
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
import { MOCK_CAMERAS, MOCK_DETECTIONS, MOCK_ALERTS, MOCK_EVIDENCE_ENVELOPES, Camera, EvidenceEnvelope } from '../../data/mockData';

export const AppShell: React.FC = () => {
  const [currentView, setCurrentView] = useState<ViewId>('overview');
  const [cameras, setCameras] = useState<Camera[]>(MOCK_CAMERAS);
  const [selectedCamera, setSelectedCamera] = useState<Camera>(MOCK_CAMERAS[4]); // CAM 07 by default
  const [activeDetections, setActiveDetections] = useState(MOCK_DETECTIONS);
  const [alerts, setAlerts] = useState(MOCK_ALERTS);
  const [evidenceEnvelopes, setEvidenceEnvelopes] = useState<EvidenceEnvelope[]>(MOCK_EVIDENCE_ENVELOPES);

  // Selected Evidence Modal state
  const [selectedEnvelope, setSelectedEnvelope] = useState<EvidenceEnvelope | null>(null);

  const handleReviewIncident = (incidentNo: string) => {
    const found = evidenceEnvelopes.find(e => e.incidentNo === incidentNo) || evidenceEnvelopes[0];
    setSelectedEnvelope(found);
  };

  const handleUpdateStatus = (incidentNo: string, newStatus: string) => {
    setEvidenceEnvelopes(prev => prev.map(ev => 
      ev.incidentNo === incidentNo ? { ...ev, status: newStatus as any } : ev
    ));
    setActiveDetections(prev => prev.map(det => 
      det.incidentNo === incidentNo ? { ...det, status: newStatus as any } : det
    ));
  };

  return (
    <div className="flex min-h-screen bg-cream font-sans text-charcoal antialiased">
      {/* 240px Sidebar Navigation Rail */}
      <Sidebar
        currentView={currentView}
        onNavigate={setCurrentView}
        activeAlertCount={alerts.length}
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
              cameras={cameras}
              selectedCamera={selectedCamera}
              onSelectCamera={setSelectedCamera}
              activeDetections={activeDetections}
              alerts={alerts}
              onReviewIncident={handleReviewIncident}
            />
          )}

          {currentView === 'live-monitor' && (
            <LiveMonitorView
              cameras={cameras}
              selectedCamera={selectedCamera}
              onSelectCamera={setSelectedCamera}
              detections={activeDetections}
              onReviewIncident={handleReviewIncident}
            />
          )}

          {currentView === 'incidents' && (
            <IncidentsView
              alerts={alerts}
              envelopes={evidenceEnvelopes}
              onReviewIncident={handleReviewIncident}
            />
          )}

          {currentView === 'analytics' && (
            <AnalyticsView />
          )}

          {currentView === 'camera-network' && (
            <CameraNetworkView
              cameras={cameras}
              onSelectCamera={(cam) => {
                setSelectedCamera(cam);
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
            onUpdateStatus={(newStatus) => handleUpdateStatus(selectedEnvelope.incidentNo, newStatus)}
          />
        </Modal>
      )}
    </div>
  );
};

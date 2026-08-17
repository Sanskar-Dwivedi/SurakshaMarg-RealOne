import React from 'react';
import { BackendCamera, BackendDetection, BackendIncident } from '../../hooks/useGauKavachStream';
import { CameraFeed } from '../dashboard/CameraFeed';
import { AlertsPanel } from '../dashboard/AlertsPanel';
import { DetectionTimeline } from '../dashboard/DetectionTimeline';
import { MonitoringMap } from '../dashboard/MonitoringMap';
import { MetricCard } from '../common/MetricCard';
import { StatusBadge } from '../common/StatusBadge';
import { AlertCircle, Camera as CamIcon, Activity, CheckCircle2, Radio } from 'lucide-react';

interface OverviewDashboardProps {
  cameras: BackendCamera[];
  selectedCamera: BackendCamera;
  onSelectCamera: (cam: BackendCamera) => void;
  detections: BackendDetection[];
  incidents: BackendIncident[];
  fps: number;
  latencyMs: number;
  status: 'CONNECTING' | 'ONLINE' | 'DEGRADED' | 'OFFLINE' | 'ERROR';
  animalCount: number;
  takeSnapshot: () => Promise<any>;
  streamUrl: string;
  onReviewIncident: (incidentNo: string) => void;
}

export const OverviewDashboard: React.FC<OverviewDashboardProps> = ({
  cameras,
  selectedCamera,
  onSelectCamera,
  detections,
  incidents,
  fps,
  latencyMs,
  status,
  animalCount,
  takeSnapshot,
  streamUrl,
  onReviewIncident,
}) => {
  // Map real backend incidents to AlertsPanel schema format
  const activeAlerts = incidents.map(inc => ({
    id: inc.id,
    incidentNo: inc.incidentNo,
    timeAgo: inc.timestamp,
    timestamp: inc.timestamp,
    title: `Animal Detected in ${inc.sector}`,
    location: inc.location,
    sector: inc.sector,
    animalType: inc.species,
    distanceToCarriagewayMeters: 1.5,
    severity: inc.severity === 'high_risk' ? ('critical' as const) : ('attention' as const),
    recommendedAction: inc.actionTaken,
    status: inc.status,
    cameraId: inc.cameraId,
  }));

  // Map real backend detections to DetectionTimeline schema format
  const timelineDetections = detections.map(det => ({
    id: det.id,
    incidentNo: `GV-${det.track_id}`,
    timestamp: new Date().toLocaleTimeString('en-IN', { hour12: false, hour: '2-digit', minute: '2-digit' }),
    timeAgo: 'Just now',
    cameraName: selectedCamera.name,
    location: selectedCamera.location,
    animalType: det.label || det.class,
    confidence: det.confidence,
    status: det.severity === 'high_risk' ? ('high_risk' as const) : ('monitored' as const),
    severity: det.severity === 'high_risk' ? ('high_risk' as const) : ('normal' as const),
    sector: selectedCamera.sector,
    boundingBoxes: [det],
  }));

  return (
    <div className="space-y-7 pb-12">
      {/* Dashboard Operational Hero Header Banner */}
      <div className="flex flex-col md:flex-row items-start md:items-center justify-between pb-4 border-2 border-tint-olive-border gap-4 bg-gradient-to-r from-tint-olive via-surface to-tint-amber p-6 rounded-2xl shadow-card">
        <div>
          <div className="flex items-center gap-2 mb-1">
            <span className="px-2.5 py-0.5 rounded-full bg-accent-olive text-cream text-[10px] font-black uppercase font-sans tracking-wider">
              CIVIC SAFETY PLATFORM
            </span>
            <span className="text-xs text-charcoal font-mono font-bold">Sector 01–08 Highway Network</span>
          </div>
          <h1 className="text-3xl sm:text-4xl font-serif font-black text-charcoal tracking-tight">
            Roadside Animal Safety Command Center
          </h1>
          <p className="text-sm text-charcoal font-bold mt-1 max-w-3xl">
            Real-time optical computer vision surveillance & carriageway hazard monitoring across connected highway cameras.
          </p>
        </div>

        <div className="flex items-center gap-3 text-xs font-mono shrink-0">
          <span className="text-charcoal font-extrabold bg-surface px-3.5 py-2 rounded-xl border-2 border-border-warm shadow-subtle">
            Real-time AI Pipeline Active
          </span>
          <span className="px-4 py-2 rounded-xl bg-accent-olive text-cream font-black border-2 border-accent-olive-dark flex items-center gap-2 shadow-card">
            <Radio className="w-4 h-4 text-accent-sand animate-pulse" />
            <span>{status === 'ONLINE' ? 'LIVE PIPELINE' : status}</span>
          </span>
        </div>
      </div>

      {/* Main Grid: Primary Camera Feed (7-8 cols) + Active Alerts (4-5 cols) */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 items-start">
        <div className="lg:col-span-8">
          <CameraFeed
            camera={selectedCamera}
            allCameras={cameras}
            onSelectCamera={onSelectCamera}
            detections={detections}
            streamUrl={streamUrl}
            fps={fps}
            latencyMs={latencyMs}
            status={status}
            onTakeSnapshot={takeSnapshot}
            onOpenIncident={onReviewIncident}
          />
        </div>

        <div className="lg:col-span-4">
          <AlertsPanel
            alerts={activeAlerts}
            onReviewAlert={onReviewIncident}
            className="h-full"
          />
        </div>
      </div>

      {/* Operational Metrics Row with Real Backend Telemetry */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-5">
        <MetricCard
          title="Animals Currently Detected"
          value={String(animalCount)}
          subtitle="Real-time YOLO object tracking count"
          trend={animalCount > 0 ? "Active" : "Normal"}
          trendType={animalCount > 0 ? "positive" : "neutral"}
          icon={Activity}
          variant="olive"
        />

        <MetricCard
          title="Active Road Alerts"
          value={String(activeAlerts.length)}
          subtitle={activeAlerts.length > 0 ? "Roadway risk condition active" : "No active roadway hazard"}
          trend={activeAlerts.length > 0 ? "Critical" : "Clear"}
          trendType={activeAlerts.length > 0 ? "negative" : "positive"}
          icon={AlertCircle}
          variant="terracotta"
          statusBadge={<StatusBadge status={activeAlerts.length > 0 ? "high_risk" : "operational"} label={`${activeAlerts.length} Open`} size="sm" />}
        />

        <MetricCard
          title="Pipeline Stream FPS"
          value={`${fps} FPS`}
          subtitle={`Latency: ${latencyMs}ms`}
          trend={status}
          trendType={status === 'ONLINE' ? "positive" : "neutral"}
          icon={CamIcon}
          variant="slate"
          statusBadge={<StatusBadge status={status === 'ONLINE' ? "operational" : "degraded"} label={`${status}`} size="sm" />}
        />

        <MetricCard
          title="Detection Model"
          value="YOLOv8"
          subtitle="GauVision Custom Cow Weights (models/cow_best.pt)"
          trend="Validated"
          trendType="positive"
          icon={CheckCircle2}
          variant="amber"
        />
      </div>

      {/* Recent Activity Timeline + Geographic Monitoring Map */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        <div className="lg:col-span-5">
          <DetectionTimeline
            detections={timelineDetections as any}
            onSelectDetection={(det) => onReviewIncident(det.incidentNo)}
          />
        </div>

        <div className="lg:col-span-7">
          <MonitoringMap
            cameras={cameras as any}
            activeDetections={timelineDetections as any}
            onSelectCamera={onSelectCamera as any}
          />
        </div>
      </div>
    </div>
  );
};

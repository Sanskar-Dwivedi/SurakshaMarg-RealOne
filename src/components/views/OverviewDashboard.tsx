import React from 'react';
import { Camera, Detection, AlertItem } from '../../data/mockData';
import { CameraFeed } from '../dashboard/CameraFeed';
import { AlertsPanel } from '../dashboard/AlertsPanel';
import { DetectionTimeline } from '../dashboard/DetectionTimeline';
import { MonitoringMap } from '../dashboard/MonitoringMap';
import { MetricCard } from '../common/MetricCard';
import { StatusBadge } from '../common/StatusBadge';
import { AlertCircle, Camera as CamIcon, Activity, CheckCircle2, Radio } from 'lucide-react';

interface OverviewDashboardProps {
  cameras: Camera[];
  selectedCamera: Camera;
  onSelectCamera: (cam: Camera) => void;
  activeDetections: Detection[];
  alerts: AlertItem[];
  onReviewIncident: (incidentNo: string) => void;
}

export const OverviewDashboard: React.FC<OverviewDashboardProps> = ({
  cameras,
  selectedCamera,
  onSelectCamera,
  activeDetections,
  alerts,
  onReviewIncident,
}) => {
  const currentFeedBoxes = selectedCamera.id === 'cam-07' 
    ? activeDetections.find(d => d.cameraId === 'cam-07')?.boundingBoxes || []
    : [];

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
            15 Aug 2026 · 15:44 IST
          </span>
          <span className="px-4 py-2 rounded-xl bg-accent-olive text-cream font-black border-2 border-accent-olive-dark flex items-center gap-2 shadow-card">
            <Radio className="w-4 h-4 text-accent-sand animate-pulse" />
            <span>Active Feed</span>
          </span>
        </div>
      </div>

      {/* Main Grid: Primary Camera Feed (7-8 cols) + Active Alerts (4-5 cols) */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        <div className="lg:col-span-8">
          <CameraFeed
            camera={selectedCamera}
            allCameras={cameras}
            onSelectCamera={onSelectCamera}
            boundingBoxes={currentFeedBoxes}
            onOpenIncident={onReviewIncident}
          />
        </div>

        <div className="lg:col-span-4">
          <AlertsPanel
            alerts={alerts}
            onReviewAlert={onReviewIncident}
            className="h-full"
          />
        </div>
      </div>

      {/* Operational Metrics Row with Vibrant Color Tints & Text-4xl Numbers */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-5">
        <MetricCard
          title="Animals Detected Today"
          value="27"
          subtitle="+4 vs yesterday (NH-44 Corridor)"
          trend="+14%"
          trendType="positive"
          icon={Activity}
          variant="olive"
        />

        <MetricCard
          title="Active Road Alerts"
          value="03"
          subtitle="Requires immediate patrol action"
          trend="Critical"
          trendType="negative"
          icon={AlertCircle}
          variant="terracotta"
          statusBadge={<StatusBadge status="high_risk" label="3 Open" size="sm" />}
        />

        <MetricCard
          title="Cameras Online"
          value="18 / 20"
          subtitle="90% network operational rate"
          trend="2 Offline"
          trendType="neutral"
          icon={CamIcon}
          variant="slate"
          statusBadge={<StatusBadge status="operational" label="90% Health" size="sm" />}
        />

        <MetricCard
          title="Detection Accuracy"
          value="94.8%"
          subtitle="GauVision v3.2 Neural Inference"
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
            detections={activeDetections}
            onSelectDetection={(det) => onReviewIncident(det.incidentNo)}
          />
        </div>

        <div className="lg:col-span-7">
          <MonitoringMap
            cameras={cameras}
            activeDetections={activeDetections}
            onSelectCamera={onSelectCamera}
          />
        </div>
      </div>
    </div>
  );
};

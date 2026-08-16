import React from 'react';
import { Camera } from '../../data/mockData';
import { StatusBadge } from '../common/StatusBadge';
import { Camera as CamIcon, Signal, RefreshCw, Cpu, Wifi } from 'lucide-react';

interface CameraNetworkViewProps {
  cameras: Camera[];
  onSelectCamera: (cam: Camera) => void;
}

export const CameraNetworkView: React.FC<CameraNetworkViewProps> = ({
  cameras,
  onSelectCamera
}) => {
  return (
    <div className="space-y-6 pb-12">
      {/* Header */}
      <div className="flex items-center justify-between pb-4 border-b border-border-warm">
        <div>
          <h1 className="text-2xl font-serif font-bold text-charcoal tracking-tight">
            Camera Network Diagnostics
          </h1>
          <p className="text-xs text-charcoal-muted mt-0.5">
            Hardware status, network telemetry, signal strength, and optical model inference diagnostics.
          </p>
        </div>

        <button className="px-3.5 py-1.5 rounded-lg bg-surface border border-border-warm text-xs font-semibold text-charcoal hover:bg-beige/60 transition-colors flex items-center gap-1.5">
          <RefreshCw className="w-3.5 h-3.5 text-accent-olive" />
          <span>Ping All Nodes</span>
        </button>
      </div>

      {/* Camera Inventory Cards Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5">
        {cameras.map((cam) => {
          return (
            <div
              key={cam.id}
              onClick={() => onSelectCamera(cam)}
              className="bg-surface border border-border-warm rounded-xl p-5 shadow-subtle hover:border-accent-olive transition-all cursor-pointer space-y-4"
            >
              <div className="flex items-start justify-between">
                <div>
                  <div className="flex items-center gap-2">
                    <span className="font-serif text-lg font-bold text-charcoal">{cam.name}</span>
                    <span className="font-mono text-[10px] bg-beige px-1.5 py-0.2 rounded text-charcoal-muted">{cam.code}</span>
                  </div>
                  <p className="text-xs text-charcoal-muted mt-0.5">{cam.location}</p>
                </div>
                <StatusBadge status={cam.status} size="sm" />
              </div>

              <div className="grid grid-cols-2 gap-3 p-3 rounded-lg bg-cream-light border border-border-warm/70 text-xs font-mono">
                <div>
                  <span className="text-charcoal-subtle text-[10px] block">LATENCY</span>
                  <span className="font-semibold text-charcoal">{cam.latencyMs > 0 ? `${cam.latencyMs} ms` : 'OFFLINE'}</span>
                </div>
                <div>
                  <span className="text-charcoal-subtle text-[10px] block">UPTIME</span>
                  <span className="font-semibold text-accent-olive">{cam.uptimePct}%</span>
                </div>
                <div>
                  <span className="text-charcoal-subtle text-[10px] block">SIGNAL</span>
                  <span className="font-semibold text-charcoal">{cam.signalDb} dBm</span>
                </div>
                <div>
                  <span className="text-charcoal-subtle text-[10px] block">DETECTIONS</span>
                  <span className="font-semibold text-charcoal">{cam.detectionsToday} today</span>
                </div>
              </div>

              <div className="flex items-center justify-between text-[11px] font-mono text-charcoal-subtle pt-2 border-t border-border-subtle">
                <span>IP: {cam.ipAddress}</span>
                <span>{cam.modelVersion}</span>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
};

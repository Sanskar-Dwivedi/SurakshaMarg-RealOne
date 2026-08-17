import React, { useState, useEffect } from 'react';
import { BackendCamera, BackendDetection } from '../../hooks/useGauKavachStream';
import { Camera as SnapshotIcon, Eye, EyeOff, Radio, RefreshCw, ChevronDown, AlertTriangle } from 'lucide-react';
import { clsx } from 'clsx';

interface CameraFeedProps {
  camera: BackendCamera;
  allCameras: BackendCamera[];
  onSelectCamera: (cam: BackendCamera) => void;
  detections?: BackendDetection[];
  streamUrl?: string;
  fps?: number;
  latencyMs?: number;
  status?: 'CONNECTING' | 'ONLINE' | 'DEGRADED' | 'OFFLINE' | 'ERROR';
  onTakeSnapshot?: () => Promise<any>;
  className?: string;
  onOpenIncident?: (incidentId: string) => void;
}

export const CameraFeed: React.FC<CameraFeedProps> = ({
  camera,
  allCameras,
  onSelectCamera,
  detections = [],
  streamUrl = 'http://localhost:8000/api/stream',
  fps = 0,
  latencyMs = 0,
  status = 'ONLINE',
  onTakeSnapshot,
  className,
  onOpenIncident
}) => {
  const [showBoxes, setShowBoxes] = useState(true);
  const [currentTime, setCurrentTime] = useState('');
  const [snapshotToast, setSnapshotToast] = useState<string | null>(null);
  const [isChangingCam, setIsChangingCam] = useState(false);
  const [imgError, setImgError] = useState(false);

  // Live IST Clock update
  useEffect(() => {
    const updateTime = () => {
      const now = new Date();
      const timeStr = now.toLocaleTimeString('en-IN', {
        hour12: false,
        hour: '2-digit',
        minute: '2-digit',
        second: '2-digit',
        timeZone: 'Asia/Kolkata'
      });
      setCurrentTime(`${timeStr} IST`);
    };

    updateTime();
    const interval = setInterval(updateTime, 1000);
    return () => clearInterval(interval);
  }, []);

  const handleSnapshot = async () => {
    if (onTakeSnapshot) {
      const res = await onTakeSnapshot();
      if (res && res.snapshot) {
        setSnapshotToast(res.snapshot.id);
      } else {
        setSnapshotToast('EV-SNAP-LIVE');
      }
    } else {
      setSnapshotToast('EV-SNAP-LIVE');
    }
    setTimeout(() => setSnapshotToast(null), 3000);
  };

  const handleCameraChange = (e: React.ChangeEvent<HTMLSelectElement>) => {
    const selected = allCameras.find(c => c.id === e.target.value);
    if (selected) {
      setIsChangingCam(true);
      setTimeout(() => {
        onSelectCamera(selected);
        setIsChangingCam(false);
      }, 300);
    }
  };

  const isOnline = status === 'ONLINE' && !imgError;

  return (
    <div className={clsx(
      'bg-charcoal text-cream-light rounded-2xl overflow-hidden shadow-subtle border border-charcoal-light flex flex-col relative z-0 isolation-auto',
      className
    )}>
      {/* Top Feed Header - Fixed Height 42px */}
      <div className="flex items-center justify-between px-3.5 py-2 bg-[#171715] border-b border-charcoal/80 text-xs shrink-0 h-[42px] select-none">
        <div className="flex items-center gap-2.5 min-w-0">
          <div className="flex items-center gap-1.5 shrink-0">
            <Radio className={clsx('w-3.5 h-3.5 animate-pulse', isOnline ? 'text-accent-olive' : 'text-status-critical')} />
            <span className="font-mono text-[11px] text-cream-dark tracking-wider font-semibold uppercase hidden sm:inline">
              LIVE FEED
            </span>
          </div>

          <span className="text-charcoal-subtle hidden sm:inline">|</span>

          {/* Camera Selection Dropdown */}
          <div className="relative inline-flex items-center min-w-0 max-w-[200px] sm:max-w-[280px]">
            <select
              value={camera.id}
              onChange={handleCameraChange}
              className="bg-charcoal-light text-cream font-medium text-xs rounded px-2 py-0.5 pr-5 border border-charcoal-muted/40 cursor-pointer focus:outline-none focus:border-accent-olive appearance-none truncate w-full"
            >
              {allCameras.map(cam => (
                <option key={cam.id} value={cam.id} className="bg-charcoal text-cream">
                  {cam.code} — {cam.location}
                </option>
              ))}
            </select>
            <ChevronDown className="w-3.5 h-3.5 text-charcoal-subtle absolute right-1.5 pointer-events-none" />
          </div>
        </div>

        <div className="flex items-center gap-2.5 shrink-0 font-mono">
          <div className={clsx(
            'flex items-center gap-1.5 px-2 py-0.5 rounded border text-[10px] sm:text-[11px] font-semibold whitespace-nowrap',
            isOnline 
              ? 'bg-accent-olive/20 text-accent-sand border-accent-olive/30' 
              : 'bg-status-critical/20 text-status-critical border-status-critical/30'
          )}>
            <span className={clsx('w-1.5 h-1.5 rounded-full animate-ping', isOnline ? 'bg-accent-olive' : 'bg-status-critical')} />
            <span>{isOnline ? 'ONLINE' : status}</span>
          </div>

          <span className="text-charcoal-subtle text-[11px] tabular-nums whitespace-nowrap hidden xs:inline">
            {fps.toFixed(1)} FPS · {latencyMs.toFixed(0)}ms
          </span>
        </div>
      </div>

      {/* Camera Video View Area - Strict 16/9 Ratio */}
      <div className="relative aspect-[16/9] w-full bg-[#121210] overflow-hidden flex items-center justify-center shrink-0">
        {/* Loading overlay during switch */}
        {isChangingCam && (
          <div className="absolute inset-0 z-30 bg-charcoal/90 flex flex-col items-center justify-center text-cream-dark gap-2">
            <RefreshCw className="w-6 h-6 animate-spin text-accent-olive" />
            <span className="text-xs font-mono">Connecting feed {camera.code}...</span>
          </div>
        )}

        {/* Real MJPEG Pipeline Video Stream */}
        {streamUrl && !imgError ? (
          <img
            src={streamUrl}
            alt="GauKavach Real-time AI Feed"
            className="w-full h-full object-cover"
            onError={() => setImgError(true)}
            onLoad={() => setImgError(false)}
          />
        ) : (
          <div className="flex flex-col items-center justify-center text-charcoal-subtle gap-3 p-6 text-center">
            <AlertTriangle className="w-10 h-10 text-status-critical animate-pulse" />
            <div>
              <p className="text-sm font-mono text-cream font-bold">STREAM OFFLINE / DISCONNECTED</p>
              <p className="text-xs font-mono text-charcoal-muted mt-1">
                Connecting to Python GauKavach Backend...
              </p>
            </div>
            <button
              onClick={() => setImgError(false)}
              className="mt-2 px-3 py-1.5 rounded bg-accent-olive/30 border border-accent-olive text-cream font-mono text-xs flex items-center gap-1.5 hover:bg-accent-olive/50"
            >
              <RefreshCw className="w-3.5 h-3.5" /> Reconnect Stream
            </button>
          </div>
        )}

        {/* Scan line overlay */}
        <div className="animate-scanline" />

        {/* Top-Left Camera Overlay Text */}
        <div className="absolute top-3 left-3 z-20 flex flex-col gap-1 pointer-events-none max-w-[70%]">
          <div className="flex items-center gap-1.5 flex-wrap">
            <span className="px-2 py-0.5 rounded bg-charcoal/80 border border-charcoal-muted/50 font-mono text-xs font-bold tracking-wider text-cream truncate">
              {camera.name}
            </span>
            <span className="px-1.5 py-0.5 rounded bg-black/70 border border-white/10 font-mono text-[10px] text-cream-dark">
              {camera.code}
            </span>
          </div>
          <p className="text-[11px] font-mono text-cream-dark/90 bg-black/50 px-2 py-0.5 rounded backdrop-blur-xs max-w-max truncate">
            {camera.location}
          </p>
        </div>

        {/* Top-Right Telemetry & Animal Count Indicator */}
        <div className="absolute top-3 right-3 z-20 flex items-center gap-2 pointer-events-none">
          {detections.length > 0 && (
            <div className="px-2.5 py-1 rounded bg-status-critical/30 border border-status-critical/50 text-status-critical text-xs font-mono font-bold flex items-center gap-1.5 backdrop-blur-xs whitespace-nowrap shadow-subtle">
              <span className="w-2 h-2 rounded-full bg-status-critical animate-ping" />
              <span>{detections.length} ANIMAL DETECTED</span>
            </div>
          )}

          <div className="px-2 py-0.5 rounded bg-black/70 border border-white/10 text-xs font-mono text-cream-dark backdrop-blur-xs tabular-nums whitespace-nowrap">
            {currentTime}
          </div>
        </div>

        {/* Computer Vision YOLO Bounding Box Overlay Layers */}
        {showBoxes && detections.map((box) => {
          const isHighRisk = box.severity === 'high_risk' || box.on_road;
          const borderColor = isHighRisk 
            ? 'border-status-critical bg-status-critical/10 text-status-critical' 
            : 'border-accent-olive bg-accent-olive/10 text-accent-sand';

          const pct = box.bbox_pct || { x: 0, y: 0, w: 0, h: 0 };

          return (
            <div
              key={box.id}
              className={clsx(
                'absolute z-20 border-2 rounded-xs transition-all duration-150 pointer-events-auto cursor-pointer hover:bg-opacity-20',
                borderColor
              )}
              style={{
                left: `${pct.x}%`,
                top: `${pct.y}%`,
                width: `${pct.w}%`,
                height: `${pct.h}%`,
              }}
              onClick={() => onOpenIncident && onOpenIncident(`GV-${box.track_id}`)}
            >
              {/* Label Tag */}
              <div className={clsx(
                'absolute -top-6 left-0 px-2 py-0.5 text-[10px] font-mono font-bold uppercase rounded-t-xs flex items-center gap-1.5 whitespace-nowrap',
                isHighRisk ? 'bg-status-critical text-cream' : 'bg-accent-olive text-cream'
              )}>
                <span>{box.label || box.class}</span>
                <span>{box.confidence}%</span>
                {box.speaker_id && <span className="px-1 bg-black/40 rounded text-[9px]">{box.speaker_id}</span>}
              </div>

              {/* Bounding Corner Crosshairs */}
              <div className="absolute -top-1 -left-1 w-2 h-2 border-t-2 border-l-2 border-current" />
              <div className="absolute -top-1 -right-1 w-2 h-2 border-t-2 border-r-2 border-current" />
              <div className="absolute -bottom-1 -left-1 w-2 h-2 border-b-2 border-l-2 border-current" />
              <div className="absolute -bottom-1 -right-1 w-2 h-2 border-b-2 border-r-2 border-current" />
            </div>
          );
        })}

        {/* Bottom Overlay Telemetry Bar - Strict Single Line Height 32px */}
        <div className="absolute bottom-2.5 left-3 right-3 z-20 flex items-center justify-between pointer-events-none gap-2">
          <div className="flex items-center gap-2.5 sm:gap-3.5 bg-black/70 backdrop-blur-xs px-2.5 py-1 rounded-lg border border-white/10 text-[10px] sm:text-[11px] font-mono text-cream-dark whitespace-nowrap overflow-hidden h-[30px] shrink-0">
            <div className="flex items-center gap-1 shrink-0">
              <span className="text-charcoal-subtle">MODEL:</span>
              <span className="text-accent-sand font-medium">{camera.modelVersion.replace('GauVision ', '')}</span>
            </div>
            <div className="flex items-center gap-1 shrink-0">
              <span className="text-charcoal-subtle">SECTOR:</span>
              <span>{camera.sector}</span>
            </div>
            <div className="hidden xs:flex items-center gap-1 shrink-0">
              <span className="text-charcoal-subtle">GPS:</span>
              <span className="tabular-nums">{(camera.coords?.lat ?? 28.4989).toFixed(4)}, {(camera.coords?.lng ?? 77.3420).toFixed(4)}</span>
            </div>
          </div>

          {/* Feed Quick Action Buttons */}
          <div className="flex items-center gap-1.5 pointer-events-auto shrink-0">
            <button
              onClick={() => setShowBoxes(!showBoxes)}
              className={clsx(
                'px-2 py-1 rounded-lg border backdrop-blur-xs text-[11px] font-mono flex items-center gap-1 transition-colors h-[30px]',
                showBoxes 
                  ? 'bg-accent-olive/40 border-accent-olive text-cream' 
                  : 'bg-black/70 border-white/10 text-charcoal-subtle hover:text-cream'
              )}
              title={showBoxes ? 'Hide Bounding Boxes' : 'Show Bounding Boxes'}
            >
              {showBoxes ? <Eye className="w-3.5 h-3.5" /> : <EyeOff className="w-3.5 h-3.5" />}
              <span className="hidden sm:inline">AI BOXES</span>
            </button>

            <button
              onClick={handleSnapshot}
              className="px-2 py-1 rounded-lg bg-black/70 hover:bg-charcoal border border-white/15 text-cream backdrop-blur-xs text-[11px] font-mono flex items-center gap-1 transition-colors h-[30px]"
              title="Capture Evidence Snapshot"
            >
              <SnapshotIcon className="w-3.5 h-3.5 text-accent-sand" />
              <span className="hidden sm:inline">SNAPSHOT</span>
            </button>
          </div>
        </div>

        {/* Snapshot Notification Toast */}
        {snapshotToast && (
          <div className="absolute top-14 right-3 z-30 bg-accent-forest text-cream px-3 py-2 rounded-lg shadow-dropdown border border-accent-olive/40 text-xs font-mono flex items-center gap-2 animate-fadeIn">
            <SnapshotIcon className="w-4 h-4 text-accent-sand" />
            <span>Snapshot saved to Evidence Archive (#{snapshotToast})</span>
          </div>
        )}
      </div>
    </div>
  );
};

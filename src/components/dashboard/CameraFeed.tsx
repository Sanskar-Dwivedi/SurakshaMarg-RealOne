import React, { useState, useEffect } from 'react';
import { Camera, BoundingBox } from '../../data/mockData';
import { Maximize2, Camera as SnapshotIcon, Eye, EyeOff, Radio, RefreshCw, ChevronDown } from 'lucide-react';
import { clsx } from 'clsx';

interface CameraFeedProps {
  camera: Camera;
  allCameras: Camera[];
  onSelectCamera: (cam: Camera) => void;
  boundingBoxes?: BoundingBox[];
  className?: string;
  onOpenIncident?: (incidentId: string) => void;
}

export const CameraFeed: React.FC<CameraFeedProps> = ({
  camera,
  allCameras,
  onSelectCamera,
  boundingBoxes = [],
  className,
  onOpenIncident
}) => {
  const [showBoxes, setShowBoxes] = useState(true);
  const [isFullscreen, setIsFullscreen] = useState(false);
  const [currentTime, setCurrentTime] = useState('');
  const [snapshotTaken, setSnapshotTaken] = useState(false);
  const [isChangingCam, setIsChangingCam] = useState(false);

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

  const handleSnapshot = () => {
    setSnapshotTaken(true);
    setTimeout(() => setSnapshotTaken(false), 2500);
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

  return (
    <div className={clsx(
      'bg-charcoal text-cream-light rounded-xl overflow-hidden shadow-subtle border border-charcoal-light flex flex-col relative z-0 isolation-auto',
      className
    )}>
      {/* Top Feed Header */}
      <div className="flex items-center justify-between px-4 py-2.5 bg-[#171715] border-b border-charcoal/80 text-xs">
        <div className="flex items-center gap-3">
          <div className="flex items-center gap-2">
            <Radio className="w-3.5 h-3.5 text-accent-olive animate-pulse" />
            <span className="font-mono text-[11px] text-cream-dark tracking-wider font-semibold uppercase">
              LIVE CAMERA FEED
            </span>
          </div>

          <span className="text-charcoal-subtle">|</span>

          {/* Camera Selection Dropdown */}
          <div className="relative inline-flex items-center">
            <select
              value={camera.id}
              onChange={handleCameraChange}
              className="bg-charcoal-light text-cream font-medium text-xs rounded px-2.5 py-1 pr-6 border border-charcoal-muted/40 cursor-pointer focus:outline-none focus:border-accent-olive appearance-none"
            >
              {allCameras.map(cam => (
                <option key={cam.id} value={cam.id} className="bg-charcoal text-cream">
                  {cam.name} — {cam.location} ({cam.status.toUpperCase()})
                </option>
              ))}
            </select>
            <ChevronDown className="w-3.5 h-3.5 text-charcoal-subtle absolute right-2 pointer-events-none" />
          </div>
        </div>

        <div className="flex items-center gap-3">
          <div className="flex items-center gap-1.5 px-2 py-0.5 rounded bg-accent-olive/20 text-accent-sand border border-accent-olive/30 text-[11px] font-mono">
            <span className="w-1.5 h-1.5 rounded-full bg-accent-olive animate-ping" />
            <span>STREAM ONLINE</span>
          </div>

          <span className="font-mono text-charcoal-subtle text-[11px]">
            {camera.fps} FPS · {camera.latencyMs}ms
          </span>
        </div>
      </div>

      {/* Camera Video View Area */}
      <div className="relative aspect-[16/9] bg-[#121210] overflow-hidden flex items-center justify-center">
        {/* Loading overlay during switch */}
        {isChangingCam && (
          <div className="absolute inset-0 z-30 bg-charcoal/90 flex flex-col items-center justify-center text-cream-dark gap-2">
            <RefreshCw className="w-6 h-6 animate-spin text-accent-olive" />
            <span className="text-xs font-mono">Connecting feed {camera.code}...</span>
          </div>
        )}

        {/* Realistic Highway Camera Vector Graphics Rendering */}
        <div className="absolute inset-0 w-full h-full pointer-events-none">
          <svg className="w-full h-full" viewBox="0 0 1000 562" preserveAspectRatio="none">
            <defs>
              {/* Road Gradient */}
              <linearGradient id="roadGrad" x1="0%" y1="0%" x2="0%" y2="100%">
                <stop offset="0%" stopColor="#2A2A26" />
                <stop offset="100%" stopColor="#1E1E1B" />
              </linearGradient>

              {/* Landscape Gradient */}
              <linearGradient id="landGrad" x1="0%" y1="0%" x2="0%" y2="100%">
                <stop offset="0%" stopColor="#353E32" />
                <stop offset="100%" stopColor="#262D24" />
              </linearGradient>

              {/* Sky Gradient */}
              <linearGradient id="skyGrad" x1="0%" y1="0%" x2="0%" y2="100%">
                <stop offset="0%" stopColor="#4A5245" />
                <stop offset="100%" stopColor="#31372E" />
              </linearGradient>
            </defs>

            {/* Sky */}
            <rect x="0" y="0" width="1000" height="220" fill="url(#skyGrad)" />

            {/* Horizon & Mountains */}
            <path d="M0,220 Q 250,180 500,220 T 1000,210 L 1000,280 L 0,280 Z" fill="#252B23" opacity="0.8" />

            {/* Landscape Fields */}
            <rect x="0" y="220" width="1000" height="342" fill="url(#landGrad)" />

            {/* Highway Asphalt Road (Perspective) */}
            <polygon points="460,220 540,220 950,562 -50,562" fill="url(#roadGrad)" />

            {/* Road Median (Concrete Barrier) */}
            <polygon points="495,220 505,220 460,562 440,562" fill="#3D3D37" />
            <polygon points="495,220 500,220 450,562 440,562" fill="#52524A" />

            {/* Lane Marking Dashes */}
            <line x1="280" y1="562" x2="480" y2="220" stroke="#C7B79B" strokeWidth="6" strokeDasharray="30 20" opacity="0.75" />
            <line x1="680" y1="562" x2="520" y2="220" stroke="#C7B79B" strokeWidth="6" strokeDasharray="30 20" opacity="0.75" />

            {/* Yellow Edge Lines */}
            <line x1="0" y1="530" x2="470" y2="220" stroke="#DCA245" strokeWidth="4" opacity="0.8" />
            <line x1="920" y1="562" x2="530" y2="220" stroke="#DCA245" strokeWidth="4" opacity="0.8" />

            {/* Roadside Trees & Utility Poles */}
            <line x1="90" y1="562" x2="380" y2="200" stroke="#1A1A17" strokeWidth="3" strokeDasharray="2 30" />
            <line x1="930" y1="562" x2="620" y2="200" stroke="#1A1A17" strokeWidth="3" strokeDasharray="2 30" />

            {/* Realistic Cattle (Bovine) Silhouette Vector Graphics in Road Sector */}
            {/* Cow 1 (On carriageway shoulder) */}
            <g transform="translate(420, 310) scale(0.95)" fill="#181816">
              {/* Body */}
              <ellipse cx="60" cy="50" rx="35" ry="22" />
              {/* Head & Horns */}
              <circle cx="24" cy="38" r="14" />
              <path d="M 18 28 C 14 20, 22 18, 26 24" stroke="#8C887E" strokeWidth="2.5" fill="none" />
              <path d="M 28 26 C 28 16, 36 18, 32 26" stroke="#8C887E" strokeWidth="2.5" fill="none" />
              {/* Legs */}
              <rect x="36" y="65" width="6" height="28" rx="2" />
              <rect x="50" y="65" width="6" height="28" rx="2" />
              <rect x="74" y="65" width="6" height="28" rx="2" />
              <rect x="88" y="65" width="6" height="28" rx="2" />
              {/* Tail */}
              <path d="M 94 46 Q 104 55 102 70" stroke="#181816" strokeWidth="3" fill="none" />
            </g>

            {/* Calf / Smaller Cattle */}
            <g transform="translate(300, 350) scale(0.65)" fill="#1F1F1C">
              <ellipse cx="50" cy="40" rx="26" ry="16" />
              <circle cx="20" cy="30" r="10" />
              <rect x="30" y="52" width="4" height="20" rx="1" />
              <rect x="42" y="52" width="4" height="20" rx="1" />
              <rect x="60" y="52" width="4" height="20" rx="1" />
              <rect x="70" y="52" width="4" height="20" rx="1" />
            </g>
          </svg>
        </div>

        {/* Scan line overlay */}
        <div className="animate-scanline" />

        {/* Top-Left Camera Overlay Text */}
        <div className="absolute top-4 left-4 z-20 flex flex-col gap-1 pointer-events-none">
          <div className="flex items-center gap-2">
            <span className="px-2 py-0.5 rounded bg-charcoal/80 border border-charcoal-muted/50 font-mono text-xs font-bold tracking-wider text-cream">
              {camera.name}
            </span>
            <span className="px-2 py-0.5 rounded bg-black/60 border border-white/10 font-mono text-[11px] text-cream-dark">
              {camera.code}
            </span>
          </div>
          <p className="text-xs font-mono text-cream-dark/90 bg-black/40 px-2 py-0.5 rounded backdrop-blur-xs max-w-max">
            {camera.location}
          </p>
        </div>

        {/* Top-Right Telemetry & Bounding Box Indicator */}
        <div className="absolute top-4 right-4 z-20 flex items-center gap-2">
          {boundingBoxes.length > 0 && (
            <div className="px-2.5 py-1 rounded bg-status-critical/20 border border-status-critical/40 text-status-critical text-xs font-mono font-semibold flex items-center gap-1.5 backdrop-blur-xs">
              <span className="w-2 h-2 rounded-full bg-status-critical animate-ping" />
              <span>{boundingBoxes.length} ANIMAL DETECTED</span>
            </div>
          )}

          <div className="px-2 py-1 rounded bg-black/60 border border-white/10 text-xs font-mono text-cream-dark backdrop-blur-xs">
            {currentTime}
          </div>
        </div>

        {/* Computer Vision Bounding Box Overlay Layers */}
        {showBoxes && boundingBoxes.map((box) => {
          const isHighRisk = box.severity === 'high_risk';
          const borderColor = isHighRisk 
            ? 'border-status-critical bg-status-critical/10 text-status-critical' 
            : 'border-accent-olive bg-accent-olive/10 text-accent-sand';

          return (
            <div
              key={box.id}
              className={clsx(
                'absolute z-20 border-2 rounded-xs transition-all duration-300 pointer-events-auto cursor-pointer hover:bg-opacity-20',
                borderColor
              )}
              style={{
                left: `${box.x}%`,
                top: `${box.y}%`,
                width: `${box.w}%`,
                height: `${box.h}%`,
              }}
              onClick={() => onOpenIncident && onOpenIncident('GV-0248')}
            >
              {/* Label Tag */}
              <div className={clsx(
                'absolute -top-6 left-0 px-2 py-0.5 text-[10px] font-mono font-bold uppercase rounded-t-xs flex items-center gap-1',
                isHighRisk ? 'bg-status-critical text-cream' : 'bg-accent-olive text-cream'
              )}>
                <span>{box.label}</span>
                <span className="opacity-90">{box.confidence}%</span>
              </div>

              {/* Bounding Corner Crosshairs */}
              <div className="absolute -top-1 -left-1 w-2 h-2 border-t-2 border-l-2 border-current" />
              <div className="absolute -top-1 -right-1 w-2 h-2 border-t-2 border-r-2 border-current" />
              <div className="absolute -bottom-1 -left-1 w-2 h-2 border-b-2 border-l-2 border-current" />
              <div className="absolute -bottom-1 -right-1 w-2 h-2 border-b-2 border-r-2 border-current" />
            </div>
          );
        })}

        {/* Bottom Overlay Telemetry Bar */}
        <div className="absolute bottom-3 left-4 right-4 z-20 flex items-center justify-between pointer-events-none">
          <div className="flex items-center gap-4 bg-black/60 backdrop-blur-xs px-3 py-1.5 rounded-lg border border-white/10 text-[11px] font-mono text-cream-dark">
            <div>
              <span className="text-charcoal-subtle">MODEL: </span>
              <span className="text-accent-sand font-medium">{camera.modelVersion}</span>
            </div>
            <div>
              <span className="text-charcoal-subtle">SECTOR: </span>
              <span>{camera.sector}</span>
            </div>
            <div>
              <span className="text-charcoal-subtle">GPS: </span>
              <span>{camera.coords.lat.toFixed(4)}, {camera.coords.lng.toFixed(4)}</span>
            </div>
          </div>

          {/* Feed Quick Action Buttons */}
          <div className="flex items-center gap-1.5 pointer-events-auto">
            <button
              onClick={() => setShowBoxes(!showBoxes)}
              className={clsx(
                'p-2 rounded-lg border backdrop-blur-xs text-xs flex items-center gap-1.5 transition-colors',
                showBoxes 
                  ? 'bg-accent-olive/30 border-accent-olive text-cream' 
                  : 'bg-black/60 border-white/10 text-charcoal-subtle hover:text-cream'
              )}
              title={showBoxes ? 'Hide Bounding Boxes' : 'Show Bounding Boxes'}
            >
              {showBoxes ? <Eye className="w-3.5 h-3.5" /> : <EyeOff className="w-3.5 h-3.5" />}
              <span className="font-mono text-[11px] hidden sm:inline">AI BOXES</span>
            </button>

            <button
              onClick={handleSnapshot}
              className="p-2 rounded-lg bg-black/60 hover:bg-charcoal border border-white/10 text-cream backdrop-blur-xs text-xs flex items-center gap-1.5 transition-colors"
              title="Capture Evidence Snapshot"
            >
              <SnapshotIcon className="w-3.5 h-3.5 text-accent-sand" />
              <span className="font-mono text-[11px] hidden sm:inline">SNAPSHOT</span>
            </button>
          </div>
        </div>

        {/* Snapshot Notification Toast */}
        {snapshotTaken && (
          <div className="absolute top-16 right-4 z-30 bg-accent-forest text-cream px-3 py-2 rounded-lg shadow-dropdown border border-accent-olive/40 text-xs font-mono flex items-center gap-2 animate-fadeIn">
            <SnapshotIcon className="w-4 h-4 text-accent-sand" />
            <span>Frame snapshot saved to Evidence Archive (#EV-SNAP-07)</span>
          </div>
        )}
      </div>
    </div>
  );
};

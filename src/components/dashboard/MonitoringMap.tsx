import React, { useState } from 'react';
import { BackendCamera } from '../../hooks/useGauKavachStream';
import { Compass, X } from 'lucide-react';
import { clsx } from 'clsx';

interface MonitoringMapProps {
  cameras: BackendCamera[];
  activeDetections: any[];
  onSelectCamera: (cam: BackendCamera) => void;
  className?: string;
}

export const MonitoringMap: React.FC<MonitoringMapProps> = ({
  cameras,
  activeDetections,
  onSelectCamera,
  className
}) => {
  const [selectedCamId, setSelectedCamId] = useState<string | null>(null);
  const [hoveredCamId, setHoveredCamId] = useState<string | null>(null);
  const [activeLayer, setActiveLayer] = useState<'cameras' | 'hotspots' | 'all'>('all');

  const activeCam = cameras.find(c => c.id === (hoveredCamId || selectedCamId));

  return (
    <div className={clsx('bg-surface border-2 border-border-warm rounded-2xl p-5 shadow-card flex flex-col', className)}>
      {/* Header */}
      <div className="flex items-center justify-between pb-4 border-b-2 border-border-warm mb-4">
        <div>
          <div className="flex items-center gap-3">
            <div className="p-2 rounded-xl bg-tint-slate border-2 border-tint-slate-border text-accent-blue shadow-subtle">
              <Compass className="w-5 h-5" />
            </div>
            <h3 className="font-serif text-xl font-black text-charcoal tracking-tight">
              Monitoring Zones & Corridors
            </h3>
          </div>
          <p className="text-xs text-charcoal font-bold mt-1">
            National Highway 44 & State Corridor Geographic Coverage
          </p>
        </div>

        {/* Map Layers Toggle */}
        <div className="flex items-center gap-1.5 bg-cream p-1.5 rounded-xl border-2 border-border-warm text-xs shadow-subtle">
          <button
            onClick={() => setActiveLayer('all')}
            className={clsx(
              'px-3.5 py-1.5 rounded-lg transition-all font-black text-xs',
              activeLayer === 'all' ? 'bg-surface text-charcoal shadow-card border border-border-warm' : 'text-charcoal-muted hover:text-charcoal'
            )}
          >
            All Corridors
          </button>
          <button
            onClick={() => setActiveLayer('hotspots')}
            className={clsx(
              'px-3.5 py-1.5 rounded-lg transition-all font-black text-xs',
              activeLayer === 'hotspots' ? 'bg-surface text-charcoal shadow-card border border-border-warm' : 'text-charcoal-muted hover:text-charcoal'
            )}
          >
            Risk Hotspots
          </button>
        </div>
      </div>

      {/* Vector Infrastructure Map SVG Container */}
      <div className="relative aspect-[16/9] w-full bg-[#E5DFC9] rounded-2xl border-2 border-border-warm overflow-hidden shadow-inner select-none">
        {/* SVG Infrastructure Map Graphic */}
        <svg className="w-full h-full" viewBox="0 0 800 450" preserveAspectRatio="xMidYMid slice">
          {/* Topographic Background Pattern */}
          <rect width="800" height="450" fill="#E3DAC5" />
          <path d="M 0 100 Q 200 120 400 80 T 800 140 L 800 0 L 0 0 Z" fill="#D6CAA4" opacity="0.6" />
          <path d="M 0 350 Q 300 380 600 320 T 800 450 L 800 450 L 0 450 Z" fill="#D6CAA4" opacity="0.5" />

          {/* Sector Boundaries */}
          <rect x="40" y="40" width="340" height="170" fill="#EEECFA" fillOpacity="0.75" stroke="#BDB7F5" strokeWidth="2.5" strokeDasharray="6 4" rx="12" />
          <text x="55" y="65" fill="#2A237A" fontSize="12" fontFamily="Outfit" fontWeight="900">SECTOR 01 - NORTH CORRIDOR</text>

          <rect x="420" y="40" width="340" height="170" fill="#FAF0D6" fillOpacity="0.75" stroke="#F2D08E" strokeWidth="2.5" strokeDasharray="6 4" rx="12" />
          <text x="435" y="65" fill="#7A4B06" fontSize="12" fontFamily="Outfit" fontWeight="900">SECTOR 02 - AGRICULTURAL BELT</text>

          <rect x="180" y="240" width="580" height="170" fill="#EAF3E6" fillOpacity="0.8" stroke="#ADD3A4" strokeWidth="2.5" strokeDasharray="6 4" rx="12" />
          <text x="195" y="265" fill="#1F4517" fontSize="12" fontFamily="Outfit" fontWeight="900">SECTOR 03 - HIGH RISK NH-44 MEDIAN</text>

          {/* Main Road Networks */}
          <path d="M 50 120 C 250 160, 450 300, 750 380" fill="none" stroke="#BDAB8E" strokeWidth="26" strokeLinecap="round" />
          <path d="M 50 120 C 250 160, 450 300, 750 380" fill="none" stroke="#1C3A24" strokeWidth="12" strokeLinecap="round" />
          <path d="M 50 120 C 250 160, 450 300, 750 380" fill="none" stroke="#FFF" strokeWidth="2" strokeDasharray="8 6" />

          {/* State Highway 12 */}
          <path d="M 120 380 C 300 300, 450 180, 720 100" fill="none" stroke="#BDAB8E" strokeWidth="18" strokeLinecap="round" />
          <path d="M 120 380 C 300 300, 450 180, 720 100" fill="none" stroke="#385C2E" strokeWidth="7" strokeLinecap="round" />

          {/* Outer Ring Road Expressway */}
          <path d="M 400 40 Q 520 220 750 250" fill="none" stroke="#AC3B1E" strokeWidth="6" strokeDasharray="5 3" />

          {/* Risk Hotspot Zones */}
          {(activeLayer === 'hotspots' || activeLayer === 'all') && (
            <>
              <circle cx="540" cy="320" r="50" fill="#AC3B1E" fillOpacity="0.25" stroke="#AC3B1E" strokeWidth="2.5" className="animate-radar" />
              <circle cx="540" cy="320" r="26" fill="#AC3B1E" fillOpacity="0.4" />
            </>
          )}

          {/* Camera Nodes */}
          {cameras.map((cam) => {
            const isSelected = (hoveredCamId || selectedCamId) === cam.id;
            const pinColor = isSelected ? '#AC3B1E' : '#385C2E';

            const xPct = cam.coords?.x ?? 40;
            const yPct = cam.coords?.y ?? 60;
            const mapX = (xPct / 100) * 800;
            const mapY = (yPct / 100) * 450;

            return (
              <g 
                key={cam.id} 
                className="cursor-pointer transition-transform duration-200"
                style={{
                  transformOrigin: `${mapX}px ${mapY}px`,
                  transform: isSelected ? 'scale(1.2)' : 'scale(1.0)',
                }}
                onMouseEnter={() => setHoveredCamId(cam.id)}
                onMouseLeave={() => setHoveredCamId(null)}
                onClick={() => {
                  setSelectedCamId(cam.id);
                  onSelectCamera(cam);
                }}
              >
                <circle cx={mapX} cy={mapY} r="28" fill={pinColor} fillOpacity="0.2" stroke={pinColor} strokeWidth="2" strokeDasharray="3 3" />
                <circle cx={mapX} cy={mapY} r="11" fill="#FFFFFF" stroke={pinColor} strokeWidth="4" />
                <circle cx={mapX} cy={mapY} r="5" fill={pinColor} />

                <rect x={mapX - 28} y={mapY + 14} width="56" height="18" fill="#141619" rx="4" opacity="0.95" />
                <text x={mapX} y={mapY + 27} fill="#FFFFFF" fontSize="10" fontFamily="Outfit" fontWeight="900" textAnchor="middle">
                  {cam.code}
                </text>
              </g>
            );
          })}

          {/* Active Incident Warning Pin */}
          <g transform="translate(540, 320)" className="animate-bounce pointer-events-none">
            <path d="M 0 -26 L 16 0 L -16 0 Z" fill="#AC3B1E" stroke="#FFF" strokeWidth="3" />
            <text x="0" y="-7" fill="#FFF" fontSize="12" fontWeight="900" textAnchor="middle">!</text>
          </g>
        </svg>

        {/* Map Legend */}
        <div className="absolute bottom-3 right-3 bg-surface/95 backdrop-blur-xs p-3 rounded-xl border-2 border-border-warm shadow-dropdown text-xs font-sans flex flex-col gap-1.5 pointer-events-none">
          <div className="flex items-center gap-2 font-black">
            <span className="w-3.5 h-3.5 rounded-full bg-accent-olive shadow-subtle" />
            <span className="text-charcoal">Operational Camera ({cameras.length})</span>
          </div>
          <div className="flex items-center gap-2 font-black">
            <span className="w-3.5 h-3.5 rounded-full bg-status-attention shadow-subtle" />
            <span className="text-charcoal">Degraded Stream (0)</span>
          </div>
          <div className="flex items-center gap-2 font-black">
            <span className="w-3.5 h-3.5 rounded-full bg-status-critical shadow-subtle" />
            <span className="text-charcoal">High-Risk Hazard Zone</span>
          </div>
        </div>

        {/* Selected Camera Tooltip Overlay */}
        {activeCam && (
          <div className="absolute top-3 left-3 bg-charcoal text-cream p-3.5 rounded-xl border-2 border-charcoal-light shadow-dropdown text-xs max-w-xs animate-fadeIn z-20">
            <div className="flex items-center justify-between font-black mb-1 gap-2">
              <span className="text-xs sm:text-sm truncate">{activeCam.name}</span>
              <button
                onClick={() => { setSelectedCamId(null); setHoveredCamId(null); }}
                className="text-charcoal-subtle hover:text-cream p-0.5"
              >
                <X className="w-3.5 h-3.5" />
              </button>
            </div>
            <p className="text-[11px] text-cream-dark font-bold">{activeCam.location}</p>
            <div className="mt-2.5 flex items-center justify-between pt-2 border-t border-white/20 text-[11px] font-mono">
              <span>STATUS: <span className="text-accent-sand font-black uppercase">{activeCam.status}</span></span>
              <span className="font-extrabold">{activeCam.detectionsToday ?? 0} detections</span>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};

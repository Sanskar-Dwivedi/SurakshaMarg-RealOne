import React, { useState } from 'react';
import { EvidenceEnvelope } from '../../data/mockData';
import { StatusBadge } from '../common/StatusBadge';
import { ShieldAlert, MapPin, Clock, Camera, FileCheck2, Send, CheckCircle2, User, AlertTriangle } from 'lucide-react';
import { clsx } from 'clsx';

interface IncidentDetailViewProps {
  envelope: EvidenceEnvelope;
  onClose: () => void;
  onUpdateStatus?: (newStatus: string) => void;
}

export const IncidentDetailView: React.FC<IncidentDetailViewProps> = ({
  envelope,
  onClose,
  onUpdateStatus
}) => {
  const [currentStatus, setCurrentStatus] = useState(envelope.status);
  const [patrolDispatched, setPatrolDispatched] = useState(envelope.status === 'Patrol Dispatched');

  const handleDispatch = () => {
    setPatrolDispatched(true);
    setCurrentStatus('Patrol Dispatched');
    if (onUpdateStatus) onUpdateStatus('Patrol Dispatched');
  };

  const handleResolve = () => {
    setCurrentStatus('Resolved');
    if (onUpdateStatus) onUpdateStatus('Resolved');
  };

  return (
    <div className="space-y-6">
      {/* Incident Header Metadata */}
      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4 pb-4 border-b border-border-warm">
        <div>
          <div className="flex items-center gap-3">
            <span className="font-mono text-lg font-bold text-charcoal">
              Incident #{envelope.incidentNo}
            </span>
            <StatusBadge status={envelope.severity} />
            <StatusBadge status={currentStatus} />
          </div>
          <p className="text-sm font-semibold text-charcoal mt-1">
            {envelope.animalType} detected near active carriageway shoulder
          </p>
        </div>

        {/* Quick Action Buttons */}
        <div className="flex items-center gap-2">
          {currentStatus !== 'Resolved' && (
            <>
              <button
                onClick={handleDispatch}
                disabled={patrolDispatched}
                className={clsx(
                  'px-3.5 py-2 rounded-lg text-xs font-semibold flex items-center gap-1.5 transition-colors shadow-subtle',
                  patrolDispatched
                    ? 'bg-beige text-charcoal-subtle border border-border-warm cursor-not-allowed'
                    : 'bg-accent-terracotta text-cream hover:bg-accent-terracotta/90 border border-accent-terracotta'
                )}
              >
                <Send className="w-3.5 h-3.5" />
                <span>{patrolDispatched ? 'Patrol Unit 04 En-Route' : 'Dispatch Patrol Unit'}</span>
              </button>

              <button
                onClick={handleResolve}
                className="px-3.5 py-2 rounded-lg bg-accent-olive text-cream hover:bg-accent-forest border border-accent-olive text-xs font-semibold flex items-center gap-1.5 transition-colors shadow-subtle"
              >
                <CheckCircle2 className="w-3.5 h-3.5 text-accent-sand" />
                <span>Mark Resolved</span>
              </button>
            </>
          )}
        </div>
      </div>

      {/* Frame Capture Media Viewer */}
      <div className="relative aspect-[16/9] bg-charcoal rounded-xl border border-charcoal-light overflow-hidden shadow-subtle flex items-center justify-center">
        {/* Realistic Canvas Vector Frame Graphic */}
        <div className="absolute inset-0 w-full h-full pointer-events-none">
          <svg className="w-full h-full" viewBox="0 0 1000 562" preserveAspectRatio="none">
            {/* Dark Camera Environment */}
            <rect width="1000" height="562" fill="#1C1C18" />
            <polygon points="450,200 550,200 950,562 -50,562" fill="#292924" />
            <line x1="280" y1="562" x2="480" y2="200" stroke="#C7B79B" strokeWidth="6" strokeDasharray="30 20" opacity="0.75" />
            <line x1="680" y1="562" x2="520" y2="200" stroke="#C7B79B" strokeWidth="6" strokeDasharray="30 20" opacity="0.75" />
            
            {/* Bovine Silhouette */}
            <g transform="translate(420, 290) scale(0.95)" fill="#121210">
              <ellipse cx="60" cy="50" rx="35" ry="22" />
              <circle cx="24" cy="38" r="14" />
              <path d="M 18 28 C 14 20, 22 18, 26 24" stroke="#8C887E" strokeWidth="2.5" fill="none" />
              <rect x="36" y="65" width="6" height="28" rx="2" />
              <rect x="50" y="65" width="6" height="28" rx="2" />
              <rect x="74" y="65" width="6" height="28" rx="2" />
              <rect x="88" y="65" width="6" height="28" rx="2" />
            </g>
          </svg>
        </div>

        {/* Bounding Box High Risk Overlay */}
        <div className="absolute left-[42%] top-[38%] w-[26%] h-[32%] border-2 border-status-critical bg-status-critical/10 rounded-xs pointer-events-none">
          <div className="absolute -top-6 left-0 px-2 py-0.5 bg-status-critical text-cream text-[10px] font-mono font-bold uppercase rounded-t-xs">
            {envelope.animalType.toUpperCase()} {envelope.confidence}%
          </div>
        </div>

        {/* Top Media Watermark */}
        <div className="absolute top-4 left-4 font-mono text-xs text-cream-dark bg-black/60 px-3 py-1 rounded backdrop-blur-xs border border-white/10">
          EVIDENTIARY FRAME CAPTURE · {envelope.cameraId}
        </div>
        <div className="absolute top-4 right-4 font-mono text-xs text-cream-dark bg-black/60 px-3 py-1 rounded backdrop-blur-xs border border-white/10">
          {envelope.timestamp}
        </div>
      </div>

      {/* Metadata Grid */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-4 bg-cream-light p-4 rounded-xl border border-border-warm text-xs">
        <div>
          <span className="text-charcoal-subtle uppercase tracking-wider text-[10px] font-semibold block">Camera ID</span>
          <span className="font-semibold text-charcoal font-mono mt-0.5 block">{envelope.cameraId}</span>
        </div>

        <div>
          <span className="text-charcoal-subtle uppercase tracking-wider text-[10px] font-semibold block">Location</span>
          <span className="font-semibold text-charcoal mt-0.5 block">{envelope.location}</span>
        </div>

        <div>
          <span className="text-charcoal-subtle uppercase tracking-wider text-[10px] font-semibold block">Speed Limit</span>
          <span className="font-semibold text-charcoal font-mono mt-0.5 block">{envelope.speedLimitKmh} km/h</span>
        </div>

        <div>
          <span className="text-charcoal-subtle uppercase tracking-wider text-[10px] font-semibold block">Weather / Light</span>
          <span className="font-semibold text-charcoal mt-0.5 block">{envelope.weatherCondition}</span>
        </div>
      </div>

      {/* Operator Notes */}
      {envelope.operatorNotes && (
        <div className="p-4 rounded-xl bg-surface border border-border-warm text-xs text-charcoal space-y-1">
          <span className="font-semibold uppercase tracking-wider text-[10px] text-charcoal-muted block">Operator Control Room Notes</span>
          <p className="leading-relaxed">{envelope.operatorNotes}</p>
        </div>
      )}

      {/* Operational Audit Timeline */}
      <div className="space-y-3 pt-2">
        <h4 className="font-serif text-base font-semibold text-charcoal">
          Audit & Operational Event Log
        </h4>

        <div className="space-y-3 pl-4 border-l-2 border-border-warm">
          {envelope.auditTrail.map((event, idx) => (
            <div key={idx} className="relative pl-6">
              <span className="absolute -left-[25px] top-0.5 w-3 h-3 rounded-full bg-accent-olive border-2 border-surface" />
              <div className="flex items-center gap-2 text-xs">
                <span className="font-mono text-charcoal-subtle font-semibold">{event.time}</span>
                <span className="font-bold text-charcoal">{event.action}</span>
                <span className="text-charcoal-muted font-medium">({event.actor})</span>
              </div>
              <p className="text-xs text-charcoal-muted mt-0.5">{event.notes}</p>
            </div>
          ))}

          {patrolDispatched && (
            <div className="relative pl-6">
              <span className="absolute -left-[25px] top-0.5 w-3 h-3 rounded-full bg-accent-terracotta border-2 border-surface animate-ping" />
              <div className="flex items-center gap-2 text-xs">
                <span className="font-mono text-status-critical font-semibold">15:24 IST</span>
                <span className="font-bold text-status-critical">Patrol Unit Dispatched</span>
                <span className="text-charcoal-muted font-medium">(Cmd. Officer S. Sharma)</span>
              </div>
              <p className="text-xs text-charcoal-muted mt-0.5">Highway Patrol Unit 04 dispatched to NH-44 KM 142.4 median segment.</p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

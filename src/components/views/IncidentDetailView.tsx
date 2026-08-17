import React, { useState } from 'react';
import { EvidenceEnvelope } from '../../data/mockData';
import { StatusBadge } from '../common/StatusBadge';
import { ShieldAlert, MapPin, Clock, Camera, FileCheck2, Send, CheckCircle2, User, AlertTriangle, RefreshCw } from 'lucide-react';
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
  const [imgError, setImgError] = useState(false);

  const videoSourceUrl = envelope.frameImage || 'http://localhost:8000/api/stream';

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

      {/* Frame Capture Real Video Viewer */}
      <div className="relative aspect-[16/9] bg-charcoal rounded-xl border border-charcoal-light overflow-hidden shadow-subtle flex items-center justify-center">
        {!imgError ? (
          <img
            src={videoSourceUrl}
            alt={`Evidentiary frame for incident ${envelope.incidentNo}`}
            className="w-full h-full object-cover"
            onError={() => setImgError(true)}
          />
        ) : (
          <div className="flex flex-col items-center justify-center text-charcoal-subtle gap-2 p-6 text-center">
            <AlertTriangle className="w-8 h-8 text-status-critical" />
            <p className="text-xs font-mono text-cream font-bold">STREAM RECONNECTING...</p>
            <button
              onClick={() => setImgError(false)}
              className="mt-1 px-3 py-1 rounded bg-accent-olive/30 border border-accent-olive text-cream font-mono text-xs flex items-center gap-1"
            >
              <RefreshCw className="w-3 h-3" /> Retry Stream
            </button>
          </div>
        )}

        {/* Top Media Watermark */}
        <div className="absolute top-4 left-4 font-mono text-xs text-cream-dark bg-black/70 px-3 py-1 rounded backdrop-blur-xs border border-white/10">
          EVIDENTIARY STREAM · {envelope.cameraId}
        </div>
        <div className="absolute top-4 right-4 font-mono text-xs text-cream-dark bg-black/70 px-3 py-1 rounded backdrop-blur-xs border border-white/10">
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

import React, { useState } from 'react';
import { MOCK_EVIDENCE_ENVELOPES, EvidenceEnvelope, AlertItem } from '../../data/mockData';
import { StatusBadge } from '../common/StatusBadge';
import { ShieldAlert, AlertTriangle, ArrowRight, Send, CheckCircle2, MapPin, Clock, Camera } from 'lucide-react';
import { clsx } from 'clsx';

interface IncidentsViewProps {
  alerts: AlertItem[];
  envelopes: EvidenceEnvelope[];
  onReviewIncident: (incidentNo: string) => void;
}

export const IncidentsView: React.FC<IncidentsViewProps> = ({
  alerts,
  envelopes,
  onReviewIncident
}) => {
  const [filterSeverity, setFilterSeverity] = useState<'all' | 'critical' | 'attention'>('all');

  const filteredAlerts = alerts.filter(a => filterSeverity === 'all' || a.severity === filterSeverity);

  return (
    <div className="space-y-6 pb-12">
      {/* Header */}
      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4 pb-4 border-b-2 border-border-warm">
        <div>
          <div className="flex items-center gap-3">
            <div className="p-2 rounded-xl bg-tint-terracotta border-2 border-tint-terracotta-border text-status-critical shadow-subtle">
              <ShieldAlert className="w-5 h-5" />
            </div>
            <h1 className="text-2xl sm:text-3xl font-serif font-black text-charcoal tracking-tight">
              Road Hazard Incidents & Patrol Dispatch
            </h1>
          </div>
          <p className="text-xs sm:text-sm text-charcoal font-bold mt-1">
            Active carriageway animal incursions requiring immediate highway patrol intervention.
          </p>
        </div>

        {/* Severity Filter Pills */}
        <div className="flex items-center gap-1.5 bg-cream p-1.5 rounded-xl border-2 border-border-warm text-xs shadow-subtle">
          <button
            onClick={() => setFilterSeverity('all')}
            className={clsx(
              'px-3.5 py-1.5 rounded-lg transition-all font-black text-xs',
              filterSeverity === 'all' ? 'bg-surface text-charcoal shadow-card border border-border-warm' : 'text-charcoal-muted hover:text-charcoal'
            )}
          >
            All Incidents ({alerts.length})
          </button>
          <button
            onClick={() => setFilterSeverity('critical')}
            className={clsx(
              'px-3.5 py-1.5 rounded-lg transition-all font-black text-xs',
              filterSeverity === 'critical' ? 'bg-status-critical text-cream shadow-card' : 'text-charcoal-muted hover:text-charcoal'
            )}
          >
            High Priority
          </button>
        </div>
      </div>

      {/* Active Incidents Cards List */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {filteredAlerts.map((alert) => {
          const isCritical = alert.severity === 'critical';
          const envelope = envelopes.find(e => e.incidentNo === alert.incidentNo);

          return (
            <div
              key={alert.id}
              className={clsx(
                'bg-surface border-2 rounded-2xl p-6 shadow-card flex flex-col justify-between space-y-4 transition-all',
                isCritical ? 'border-tint-terracotta-border bg-gradient-to-b from-tint-terracotta/40 to-surface' : 'border-tint-amber-border bg-gradient-to-b from-tint-amber/40 to-surface'
              )}
            >
              <div>
                {/* Header row */}
                <div className="flex items-center justify-between gap-2 pb-3 border-b border-black/10">
                  <div className="flex items-center gap-2">
                    <span className={clsx(
                      'text-xs font-mono font-black uppercase tracking-wider px-3 py-1 rounded-lg shadow-subtle',
                      isCritical ? 'bg-status-critical text-cream' : 'bg-status-attention text-cream'
                    )}>
                      {isCritical ? 'CRITICAL HAZARD' : 'MONITORING'}
                    </span>
                    <span className="font-mono text-sm font-black text-charcoal bg-surface px-2.5 py-0.5 rounded-md border border-black/10">
                      #{alert.incidentNo}
                    </span>
                  </div>

                  <span className="text-xs font-mono font-black text-charcoal">
                    {alert.timeAgo}
                  </span>
                </div>

                {/* Title & Location */}
                <div className="mt-4 space-y-1">
                  <h3 className="text-lg font-serif font-black text-charcoal leading-snug">
                    {alert.title}
                  </h3>
                  <div className="flex items-center gap-3 text-xs font-bold text-charcoal pt-1">
                    <span className="flex items-center gap-1">
                      <Camera className="w-3.5 h-3.5 text-accent-olive" />
                      <span>{alert.cameraId}</span>
                    </span>
                    <span>·</span>
                    <span className="flex items-center gap-1">
                      <MapPin className="w-3.5 h-3.5 text-accent-terracotta" />
                      <span>{alert.location}</span>
                    </span>
                  </div>
                </div>

                {/* Metadata Grid */}
                <div className="grid grid-cols-2 gap-3 mt-4 p-3.5 rounded-xl bg-surface border border-black/10 text-xs shadow-subtle">
                  <div>
                    <span className="text-charcoal-subtle font-extrabold text-[10px] uppercase block">Animal Subject</span>
                    <span className="font-black text-charcoal text-sm">{alert.animalType}</span>
                  </div>
                  <div>
                    <span className="text-charcoal-subtle font-extrabold text-[10px] uppercase block">Distance To Lane</span>
                    <span className="font-mono font-black text-status-critical text-sm">{alert.distanceToCarriagewayMeters} meters</span>
                  </div>
                </div>

                {/* Recommended Action */}
                <div className="mt-3 p-3 rounded-xl bg-cream-light border border-black/10 text-xs font-bold text-charcoal flex items-start gap-2.5">
                  <AlertTriangle className="w-4 h-4 text-accent-terracotta shrink-0 mt-0.5" />
                  <span>{alert.recommendedAction}</span>
                </div>
              </div>

              {/* Footer Actions */}
              <div className="pt-3 border-t border-black/10 flex items-center justify-between gap-3">
                <StatusBadge status={envelope?.status || 'Open'} />

                <button
                  onClick={() => onReviewIncident(alert.incidentNo)}
                  className="px-4 py-2.5 rounded-xl bg-accent-olive hover:bg-accent-forest text-cream font-black text-xs flex items-center gap-2 shadow-card transition-colors"
                >
                  <span>Inspect Incident & Evidence</span>
                  <ArrowRight className="w-4 h-4 text-accent-sand" />
                </button>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
};

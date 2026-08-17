import React from 'react';
import { AlertItem } from '../../data/mockData';
import { AlertTriangle, ShieldAlert, ArrowRight, CheckCircle2 } from 'lucide-react';
import { clsx } from 'clsx';

interface AlertsPanelProps {
  alerts: AlertItem[];
  onReviewAlert: (incidentNo: string) => void;
  className?: string;
}

export const AlertsPanel: React.FC<AlertsPanelProps> = ({
  alerts,
  onReviewAlert,
  className
}) => {
  return (
    <div className={clsx(
      'bg-surface border-2 border-border-warm rounded-2xl p-5 shadow-card flex flex-col justify-between',
      className
    )}>
      <div>
        <div className="flex items-center justify-between pb-4 border-b-2 border-border-warm mb-4">
          <div className="flex items-center gap-3">
            <div className="p-2 rounded-xl bg-tint-terracotta border-2 border-tint-terracotta-border text-status-critical shadow-subtle">
              <ShieldAlert className="w-5 h-5" />
            </div>
            <h3 className="font-serif text-xl font-black text-charcoal tracking-tight">
              Requires Attention
            </h3>
          </div>
          <span className="text-xs font-mono px-3 py-1 rounded-full bg-status-critical text-cream font-black shadow-subtle">
            {alerts.length} Active
          </span>
        </div>

        <div className="space-y-4 max-h-[520px] overflow-y-auto pr-1">
          {alerts.map((alert) => {
            const isCritical = alert.severity === 'critical';
            return (
              <div
                key={alert.id}
                className={clsx(
                  'p-4 rounded-xl border-2 transition-all duration-200 flex flex-col gap-3 shadow-card',
                  isCritical
                    ? 'bg-tint-terracotta border-tint-terracotta-border hover:border-status-critical'
                    : 'bg-tint-amber border-tint-amber-border hover:border-accent-amber'
                )}
              >
                <div className="flex items-start justify-between gap-2">
                  <div className="flex items-center gap-2">
                    <span className={clsx(
                      'text-[11px] font-mono font-black uppercase tracking-wider px-2.5 py-0.5 rounded-md shadow-subtle',
                      isCritical ? 'bg-status-critical text-cream' : 'bg-status-attention text-cream'
                    )}>
                      {isCritical ? 'HIGH PRIORITY' : 'MONITORING'}
                    </span>
                    <span className="text-xs text-charcoal font-mono font-black">
                      {alert.timeAgo}
                    </span>
                  </div>

                  <span className="text-xs font-mono font-black text-charcoal bg-surface px-2.5 py-0.5 rounded-md border border-black/10 shadow-subtle">
                    {alert.cameraId}
                  </span>
                </div>

                <div>
                  <h4 className="text-base sm:text-lg font-serif font-black text-charcoal tracking-tight leading-snug">
                    {alert.title}
                  </h4>
                  <p className="text-xs text-charcoal font-bold mt-1">
                    {alert.location} · <span className="text-accent-terracotta font-black underline">{alert.animalType}</span>
                  </p>
                </div>

                <div className="text-xs text-charcoal bg-surface p-3 rounded-xl border border-black/10 flex items-start gap-2 shadow-subtle">
                  <AlertTriangle className="w-4 h-4 text-accent-terracotta shrink-0 mt-0.5" />
                  <span className="font-bold leading-relaxed">{alert.recommendedAction}</span>
                </div>

                <div className="flex items-center justify-end pt-1">
                  <button
                    onClick={() => onReviewAlert(alert.incidentNo)}
                    className="inline-flex items-center gap-2 text-xs font-black text-cream hover:bg-accent-forest transition-colors bg-accent-olive px-3.5 py-2 rounded-xl border border-accent-olive-dark shadow-card"
                  >
                    <span>Review Incident #{alert.incidentNo}</span>
                    <ArrowRight className="w-4 h-4 text-accent-sand" />
                  </button>
                </div>
              </div>
            );
          })}

          {alerts.length === 0 && (
            <div className="py-8 text-center text-charcoal flex flex-col items-center gap-2">
              <CheckCircle2 className="w-10 h-10 text-accent-olive" />
              <p className="text-base font-black">No active incidents requiring immediate attention</p>
              <p className="text-xs text-charcoal-muted font-bold">All roadside sectors reporting normal operational conditions.</p>
            </div>
          )}
        </div>
      </div>

      <div className="pt-4 border-t-2 border-border-warm mt-4 text-xs font-black text-charcoal flex items-center justify-between">
        <span>Auto-escalation threshold: 3 mins</span>
        <span className="font-mono text-accent-olive bg-tint-olive px-2.5 py-1 rounded-lg border border-tint-olive-border font-black">System Operational</span>
      </div>
    </div>
  );
};

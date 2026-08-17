import React from 'react';
import { Detection } from '../../data/mockData';
import { StatusBadge } from '../common/StatusBadge';
import { Activity, ChevronRight } from 'lucide-react';
import { clsx } from 'clsx';

interface DetectionTimelineProps {
  detections: Detection[];
  onSelectDetection: (det: Detection) => void;
  className?: string;
}

export const DetectionTimeline: React.FC<DetectionTimelineProps> = ({
  detections,
  onSelectDetection,
  className
}) => {
  return (
    <div className={clsx('bg-surface border-2 border-border-warm rounded-2xl p-5 shadow-card', className)}>
      <div className="flex items-center justify-between pb-4 border-b-2 border-border-warm mb-3.5">
        <div className="flex items-center gap-3">
          <div className="p-2 rounded-xl bg-tint-olive border-2 border-tint-olive-border text-accent-olive shadow-subtle">
            <Activity className="w-5 h-5" />
          </div>
          <h3 className="font-serif text-xl font-black text-charcoal tracking-tight">
            Recent Detections
          </h3>
        </div>
        <span className="text-xs font-mono font-black text-accent-olive bg-tint-olive px-3 py-1 rounded-full border border-tint-olive-border shadow-subtle">
          Real-time Stream
        </span>
      </div>

      <div className="divide-y-2 divide-border-warm/60">
        {detections.map((det) => {
          return (
            <div
              key={det.id}
              onClick={() => onSelectDetection(det)}
              className="py-3.5 flex items-center justify-between gap-3 hover:bg-tint-olive/50 px-3 rounded-xl transition-all cursor-pointer group"
            >
              <div className="flex items-center gap-3">
                <span className="font-mono text-xs text-charcoal font-black w-14 bg-tint-amber px-2 py-1 rounded-lg border border-tint-amber-border text-center shadow-subtle">
                  {(det.timestamp || det.timeAgo || '15:36').substring(0, 5)}
                </span>

                <div>
                  <div className="flex items-center gap-2">
                    <span className="text-base font-serif font-black text-charcoal tracking-tight group-hover:text-accent-olive transition-colors">
                      {det.animalType}
                    </span>
                    <span className="text-[10px] font-mono font-black text-accent-olive bg-tint-olive px-2 py-0.5 rounded-md border border-tint-olive-border">
                      {det.confidence}% conf
                    </span>
                  </div>
                  <p className="text-xs text-charcoal font-bold mt-0.5">
                    <span className="font-mono font-black text-accent-blue underline">{det.cameraName}</span> · {det.location}
                  </p>
                </div>
              </div>

              <div className="flex items-center gap-3 shrink-0">
                <StatusBadge status={det.severity} size="sm" />
                <ChevronRight className="w-5 h-5 text-charcoal-subtle group-hover:text-charcoal group-hover:translate-x-1 transition-all" />
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
};

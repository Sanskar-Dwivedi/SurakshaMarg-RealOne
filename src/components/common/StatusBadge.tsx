import React from 'react';
import { clsx } from 'clsx';

export type StatusType = 
  | 'online' | 'operational' | 'resolved' | 'low'
  | 'attention' | 'caution' | 'under_review' | 'moderate'
  | 'critical' | 'high_risk' | 'open' | 'severe'
  | 'offline' | 'disabled';

interface StatusBadgeProps {
  status: StatusType | string;
  label?: string;
  size?: 'sm' | 'md';
  pulse?: boolean;
  className?: string;
}

export const StatusBadge: React.FC<StatusBadgeProps> = ({
  status,
  label,
  size = 'md',
  pulse = false,
  className
}) => {
  const normStatus = status.toLowerCase().replace(' ', '_');

  let dotColor = 'bg-accent-olive';
  let badgeBg = 'bg-tint-olive';
  let badgeText = 'text-tint-olive-text';
  let badgeBorder = 'border-tint-olive-border';

  if (['attention', 'caution', 'under_review', 'moderate'].includes(normStatus)) {
    dotColor = 'bg-status-attention';
    badgeBg = 'bg-tint-amber';
    badgeText = 'text-tint-amber-text';
    badgeBorder = 'border-tint-amber-border';
  } else if (['critical', 'high_risk', 'open', 'severe'].includes(normStatus)) {
    dotColor = 'bg-status-critical';
    badgeBg = 'bg-tint-terracotta';
    badgeText = 'text-tint-terracotta-text';
    badgeBorder = 'border-tint-terracotta-border';
  } else if (['offline', 'disabled'].includes(normStatus)) {
    dotColor = 'bg-charcoal-subtle';
    badgeBg = 'bg-cream-dark';
    badgeText = 'text-charcoal';
    badgeBorder = 'border-border-warm';
  }

  const displayText = label || status.replace('_', ' ').toUpperCase();

  return (
    <span className={clsx(
      'inline-flex items-center gap-1.5 font-bold border rounded-md tracking-wider transition-colors shadow-subtle',
      size === 'sm' ? 'px-2 py-0.5 text-[10px]' : 'px-2.5 py-1 text-xs',
      badgeBg,
      badgeText,
      badgeBorder,
      className
    )}>
      <span className="relative flex h-2 w-2">
        {pulse && (
          <span className={clsx(
            'animate-ping absolute inline-flex h-full w-full rounded-full opacity-75',
            dotColor
          )} />
        )}
        <span className={clsx('relative inline-flex rounded-full h-2 w-2', dotColor)} />
      </span>
      <span className="uppercase font-sans">{displayText}</span>
    </span>
  );
};

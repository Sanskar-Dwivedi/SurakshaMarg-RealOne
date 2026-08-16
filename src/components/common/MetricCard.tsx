import React from 'react';
import { clsx } from 'clsx';
import { LucideIcon } from 'lucide-react';

export type MetricVariant = 'olive' | 'amber' | 'terracotta' | 'slate' | 'indigo' | 'default';

interface MetricCardProps {
  title: string;
  value: string | number;
  subtitle?: string;
  trend?: string;
  trendType?: 'positive' | 'negative' | 'neutral';
  icon?: LucideIcon;
  statusBadge?: React.ReactNode;
  variant?: MetricVariant;
  active?: boolean;
  className?: string;
  onClick?: () => void;
}

export const MetricCard: React.FC<MetricCardProps> = ({
  title,
  value,
  subtitle,
  trend,
  trendType = 'neutral',
  icon: Icon,
  statusBadge,
  variant = 'default',
  active = false,
  className,
  onClick
}) => {
  const variantStyles = {
    olive: {
      bg: 'bg-tint-olive/95 hover:bg-tint-olive',
      border: 'border-tint-olive-border/90 hover:border-accent-olive',
      iconBg: 'bg-accent-olive text-cream shadow-subtle',
      valueText: 'text-tint-olive-text font-sans font-black',
      titleColor: 'text-accent-olive-dark',
    },
    amber: {
      bg: 'bg-tint-amber/95 hover:bg-tint-amber',
      border: 'border-tint-amber-border/90 hover:border-accent-amber',
      iconBg: 'bg-accent-amber text-cream shadow-subtle',
      valueText: 'text-tint-amber-text font-sans font-black',
      titleColor: 'text-tint-amber-text',
    },
    terracotta: {
      bg: 'bg-tint-terracotta/95 hover:bg-tint-terracotta',
      border: 'border-tint-terracotta-border/90 hover:border-accent-terracotta',
      iconBg: 'bg-accent-terracotta text-cream shadow-subtle',
      valueText: 'text-tint-terracotta-text font-sans font-black',
      titleColor: 'text-tint-terracotta-text',
    },
    slate: {
      bg: 'bg-tint-slate/95 hover:bg-tint-slate',
      border: 'border-tint-slate-border/90 hover:border-accent-blue',
      iconBg: 'bg-accent-blue text-cream shadow-subtle',
      valueText: 'text-tint-slate-text font-sans font-black',
      titleColor: 'text-tint-slate-text',
    },
    indigo: {
      bg: 'bg-tint-indigo/95 hover:bg-tint-indigo',
      border: 'border-tint-indigo-border/90 hover:border-accent-indigo',
      iconBg: 'bg-accent-indigo text-cream shadow-subtle',
      valueText: 'text-tint-indigo-text font-sans font-black',
      titleColor: 'text-tint-indigo-text',
    },
    default: {
      bg: 'bg-surface hover:bg-surface-light',
      border: 'border-border-warm hover:border-border-strong',
      iconBg: 'bg-charcoal text-cream shadow-subtle',
      valueText: 'text-charcoal font-sans font-black',
      titleColor: 'text-charcoal-muted',
    }
  }[variant];

  return (
    <div 
      onClick={onClick}
      className={clsx(
        'border-2 rounded-xl p-5 transition-all duration-200 shadow-card flex flex-col justify-between',
        variantStyles.bg,
        variantStyles.border,
        active ? 'ring-2 ring-accent-olive shadow-dropdown' : '',
        onClick ? 'cursor-pointer' : '',
        className
      )}
    >
      <div>
        <div className="flex items-center justify-between gap-2 mb-3">
          <span className={clsx('text-[11px] font-black tracking-widest uppercase font-sans', variantStyles.titleColor)}>
            {title}
          </span>
          {Icon && (
            <div className={clsx('p-2 rounded-lg shrink-0', variantStyles.iconBg)}>
              <Icon className="w-4 h-4" />
            </div>
          )}
        </div>

        <div className="flex items-baseline justify-between gap-2 mt-1">
          <span className={clsx('text-4xl sm:text-5xl font-extrabold tracking-tight font-sans', variantStyles.valueText)}>
            {value}
          </span>
          {statusBadge}
        </div>
      </div>

      <div className="mt-4 pt-3 border-t border-black/10 flex items-center justify-between gap-2">
        {subtitle && (
          <p className="text-xs text-charcoal font-bold leading-snug">
            {subtitle}
          </p>
        )}
        {trend && (
          <span className={clsx(
            'text-[11px] font-black px-2.5 py-0.5 rounded-md font-mono shrink-0 shadow-subtle',
            trendType === 'positive' ? 'bg-accent-olive text-cream' :
            trendType === 'negative' ? 'bg-accent-terracotta text-cream' :
            'bg-black/10 text-charcoal'
          )}>
            {trend}
          </span>
        )}
      </div>
    </div>
  );
};

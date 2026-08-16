import React from 'react';
import { Bell, RefreshCw } from 'lucide-react';
import { ViewId } from './Sidebar';

interface HeaderProps {
  currentView: ViewId;
  onOpenNotifications?: () => void;
}

export const Header: React.FC<HeaderProps> = ({ currentView, onOpenNotifications }) => {
  const getPageInfo = (view: ViewId) => {
    switch (view) {
      case 'overview':
        return { title: 'Dashboard Command Center', subtitle: 'Roadside animal monitoring & real-time risk detection' };
      case 'live-monitor':
        return { title: 'Live Camera Surveillance Network', subtitle: 'Multi-corridor high-definition camera stream array' };
      case 'camera-network':
        return { title: 'Camera Telemetry & Node Health', subtitle: 'Hardware status, signal quality, and sensor diagnostics' };
      case 'incidents':
        return { title: 'Road Safety Hazard Incidents', subtitle: 'Active carriageway hazard alerts requiring patrol response' };
      case 'analytics':
        return { title: 'Operational Risk Analytics', subtitle: 'Historical risk trends, peak hours, and corridor density' };
      case 'settings':
        return { title: 'System Parameters & AI Calibration', subtitle: 'GauVision model thresholds, alert webhooks, and sector bounds' };
      default:
        return { title: 'Dashboard Command Center', subtitle: 'Roadside animal monitoring & detection' };
    }
  };

  const { title, subtitle } = getPageInfo(currentView);

  return (
    <header className="min-h-16 py-3 bg-surface border-b-2 border-border-warm px-6 sm:px-8 flex items-center justify-between sticky top-0 z-40 shadow-card">
      {/* Left Title & Subtitle */}
      <div className="flex-1 min-w-0 pr-4">
        <h2 className="text-xl sm:text-2xl font-serif font-black text-charcoal tracking-tight truncate">
          {title}
        </h2>
        <p className="text-xs text-charcoal font-bold mt-0.5 truncate">
          {subtitle}
        </p>
      </div>

      {/* Right Header Metadata & Telemetry */}
      <div className="flex items-center gap-3 sm:gap-4 shrink-0">
        {/* System Status Indicator */}
        <div className="flex items-center gap-2 px-3 py-1.5 rounded-xl bg-tint-olive text-tint-olive-text border-2 border-tint-olive-border text-xs font-black font-sans shadow-subtle">
          <span className="w-2.5 h-2.5 rounded-full bg-accent-olive animate-pulse" />
          <span className="hidden sm:inline">System Operational</span>
          <span className="sm:hidden">Operational</span>
        </div>

        {/* Sync Time */}
        <div className="hidden lg:flex items-center gap-2 text-xs text-charcoal font-mono bg-tint-amber px-3 py-1.5 rounded-xl border border-tint-amber-border font-bold">
          <RefreshCw className="w-3.5 h-3.5 text-accent-amber animate-spin" />
          <span>16:01 IST</span>
        </div>

        {/* Notifications */}
        <button
          onClick={onOpenNotifications}
          className="relative p-2 rounded-xl text-charcoal hover:bg-tint-terracotta transition-colors border-2 border-border-warm bg-cream-light shadow-subtle"
          aria-label="View notifications"
        >
          <Bell className="w-4.5 h-4.5 text-charcoal" />
          <span className="absolute top-1 right-1 w-2.5 h-2.5 rounded-full bg-status-critical shadow-subtle" />
        </button>

        {/* Administrator Profile */}
        <div className="flex items-center gap-2.5 pl-3 border-l-2 border-border-warm">
          <div className="w-9 h-9 rounded-xl bg-accent-forest text-accent-sand border-2 border-accent-olive flex items-center justify-center font-black text-xs font-serif shadow-subtle">
            OP
          </div>
          <div className="hidden xl:block text-xs">
            <p className="font-black text-charcoal leading-none text-xs">Cmd. Officer S. Sharma</p>
            <p className="text-[10px] text-accent-olive font-extrabold mt-1">Control Room Sector 03</p>
          </div>
        </div>
      </div>
    </header>
  );
};

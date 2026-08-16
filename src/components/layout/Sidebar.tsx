import React from 'react';
import { 
  LayoutDashboard, 
  Video, 
  Camera as CameraIcon, 
  AlertTriangle, 
  BarChart3, 
  Settings,
  Shield
} from 'lucide-react';
import { clsx } from 'clsx';

export type ViewId = 
  | 'overview' 
  | 'live-monitor' 
  | 'camera-network' 
  | 'incidents' 
  | 'analytics' 
  | 'settings';

interface SidebarProps {
  currentView: ViewId;
  onNavigate: (view: ViewId) => void;
  activeAlertCount?: number;
}

export const Sidebar: React.FC<SidebarProps> = ({
  currentView,
  onNavigate,
  activeAlertCount = 3
}) => {
  const navSections = [
    {
      title: 'Monitoring',
      accentColor: 'text-accent-olive font-black',
      dotBg: 'bg-accent-olive',
      items: [
        { id: 'overview', label: 'Overview', icon: LayoutDashboard },
        { id: 'live-monitor', label: 'Live Monitor', icon: Video },
        { id: 'camera-network', label: 'Camera Network', icon: CameraIcon },
      ]
    },
    {
      title: 'Intelligence',
      accentColor: 'text-accent-terracotta font-black',
      dotBg: 'bg-accent-terracotta',
      items: [
        { id: 'incidents', label: 'Incidents', icon: AlertTriangle, badge: activeAlertCount },
        { id: 'analytics', label: 'Analytics', icon: BarChart3 },
      ]
    },
    {
      title: 'Administration',
      accentColor: 'text-charcoal-muted font-black',
      dotBg: 'bg-charcoal-subtle',
      items: [
        { id: 'settings', label: 'Settings', icon: Settings },
      ]
    }
  ];

  return (
    <aside className="w-[240px] bg-cream-dark border-r-2 border-border-warm flex flex-col justify-between h-screen sticky top-0 shrink-0 select-none z-50 shadow-card">
      <div>
        {/* Brand Header */}
        <div className="p-5 border-b-2 border-border-warm bg-tint-olive/40">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl bg-accent-olive text-cream flex items-center justify-center shadow-card border-2 border-accent-olive-dark">
              <Shield className="w-5 h-5 text-accent-sand" />
            </div>
            <div>
              <h1 className="font-serif text-2xl font-black tracking-tight text-charcoal leading-none">
                GAUKAVACH
              </h1>
              <p className="text-[11px] font-sans font-black text-accent-olive mt-1 tracking-wider uppercase">
                Road Safety Command
              </p>
            </div>
          </div>
        </div>

        {/* Navigation Links */}
        <div className="px-3 py-5 space-y-6 overflow-y-auto custom-scrollbar">
          {navSections.map((section) => (
            <div key={section.title}>
              <div className="px-3 flex items-center gap-2 mb-2">
                <span className={clsx('w-2 h-2 rounded-full', section.dotBg)} />
                <span className={clsx('text-[11px] tracking-widest uppercase font-sans', section.accentColor)}>
                  {section.title}
                </span>
                <span className="h-[1.5px] flex-1 bg-border-warm" />
              </div>

              <ul className="space-y-1">
                {section.items.map((item) => {
                  const Icon = item.icon;
                  const isActive = currentView === item.id;
                  return (
                    <li key={item.id}>
                      <button
                        onClick={() => onNavigate(item.id as ViewId)}
                        className={clsx(
                          'w-full flex items-center justify-between px-3.5 py-2.5 rounded-xl text-xs font-black transition-all duration-150 relative group',
                          isActive
                            ? 'bg-surface text-charcoal font-black shadow-card border-l-4 border-accent-olive text-sm'
                            : 'text-charcoal-muted hover:text-charcoal hover:bg-surface/80'
                        )}
                      >
                        <div className="flex items-center gap-3">
                          <Icon className={clsx('w-4 h-4 transition-colors', isActive ? 'text-accent-olive' : 'text-charcoal-subtle group-hover:text-charcoal')} />
                          <span className="tracking-tight">{item.label}</span>
                        </div>
                        {item.badge !== undefined && item.badge > 0 && (
                          <span className={clsx(
                            'text-[11px] font-mono px-2.5 py-0.5 rounded-full font-black shadow-subtle',
                            isActive ? 'bg-accent-terracotta text-cream' : 'bg-status-critical text-cream'
                          )}>
                            {item.badge}
                          </span>
                        )}
                      </button>
                    </li>
                  );
                })}
              </ul>
            </div>
          ))}
        </div>
      </div>

      {/* Sidebar Footer — Government System Telemetry */}
      <div className="p-4 border-t-2 border-border-warm bg-surface/70 text-[11px] text-charcoal flex flex-col gap-2">
        <div className="flex items-center justify-between font-mono">
          <span className="text-charcoal-subtle font-bold text-[10px]">GOVT DEPT ID:</span>
          <span className="font-extrabold text-accent-forest bg-tint-olive px-2 py-0.5 rounded border border-tint-olive-border">NHAI-CRS-08</span>
        </div>
        <div className="flex items-center justify-between font-mono text-[10px]">
          <span className="text-charcoal-subtle font-bold">GauVision AI:</span>
          <span className="text-accent-olive font-black bg-tint-amber px-2 py-0.5 rounded border border-tint-amber-border">v3.2 Active</span>
        </div>
      </div>
    </aside>
  );
};

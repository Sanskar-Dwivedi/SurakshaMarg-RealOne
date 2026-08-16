import React from 'react';
import { HOURLY_DETECTION_STATS, CAMERA_SECTOR_STATS } from '../../data/mockData';
import { 
  ResponsiveContainer, 
  LineChart, 
  Line, 
  XAxis, 
  YAxis, 
  Tooltip, 
  CartesianGrid, 
  BarChart, 
  Bar 
} from 'recharts';
import { BarChart3, TrendingUp, ShieldCheck, MapPin } from 'lucide-react';

export const AnalyticsView: React.FC = () => {
  return (
    <div className="space-y-6 pb-12">
      {/* Header */}
      <div className="flex items-center justify-between pb-4 border-b border-border-warm">
        <div>
          <h1 className="text-2xl font-serif font-bold text-charcoal tracking-tight">
            Operational Analytics & Risk Trends
          </h1>
          <p className="text-xs text-charcoal-muted mt-0.5">
            Aggregated computer vision detection metrics across national highway corridors.
          </p>
        </div>

        <div className="flex items-center gap-2 text-xs font-mono text-charcoal-subtle">
          <span>Period: Today (15 Aug 2026)</span>
        </div>
      </div>

      {/* Top Chart Row: Hourly Detection Trend (Line Chart) */}
      <div className="bg-surface border border-border-warm rounded-xl p-5 shadow-subtle space-y-4">
        <div className="flex items-center justify-between">
          <div>
            <h3 className="font-serif text-lg font-semibold text-charcoal">
              Hourly Detections & High-Risk Frequency
            </h3>
            <p className="text-xs text-charcoal-muted mt-0.5">
              Comparison between total animal presence and high-risk carriageway incursions.
            </p>
          </div>

          <div className="flex items-center gap-4 text-xs font-sans">
            <div className="flex items-center gap-1.5">
              <span className="w-3 h-0.5 bg-accent-olive" />
              <span className="text-charcoal font-medium">Total Detections</span>
            </div>
            <div className="flex items-center gap-1.5">
              <span className="w-3 h-0.5 bg-status-critical" />
              <span className="text-charcoal font-medium">High-Risk Incursions</span>
            </div>
          </div>
        </div>

        <div className="h-64 w-full pt-2">
          <ResponsiveContainer width="100%" height="100%">
            <LineChart data={HOURLY_DETECTION_STATS} margin={{ top: 5, right: 20, left: -20, bottom: 5 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="#EDE7DA" />
              <XAxis dataKey="hour" stroke="#817B70" fontSize={11} tickLine={false} />
              <YAxis stroke="#817B70" fontSize={11} tickLine={false} />
              <Tooltip 
                contentStyle={{ 
                  backgroundColor: '#FCFBF7', 
                  borderColor: '#DCD6CA', 
                  borderRadius: '8px',
                  fontSize: '12px',
                  boxShadow: '0 2px 8px rgba(32,32,29,0.08)' 
                }} 
              />
              <Line 
                type="monotone" 
                dataKey="detections" 
                stroke="#59634D" 
                strokeWidth={2} 
                dot={{ fill: '#59634D', r: 4 }} 
                activeDot={{ r: 6 }} 
              />
              <Line 
                type="monotone" 
                dataKey="highRisk" 
                stroke="#A65F45" 
                strokeWidth={2} 
                strokeDasharray="4 4"
                dot={{ fill: '#A65F45', r: 4 }} 
              />
            </LineChart>
          </ResponsiveContainer>
        </div>
      </div>

      {/* Bottom Row: Sector Breakdown & Species Distribution */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        {/* Sector Risk Bar Chart */}
        <div className="lg:col-span-7 bg-surface border border-border-warm rounded-xl p-5 shadow-subtle space-y-4">
          <div>
            <h3 className="font-serif text-lg font-semibold text-charcoal">
              Sector Density & Detection Count
            </h3>
            <p className="text-xs text-charcoal-muted mt-0.5">
              Accumulated detection incidents per highway monitoring sector.
            </p>
          </div>

          <div className="h-56 w-full pt-2">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={CAMERA_SECTOR_STATS} margin={{ top: 5, right: 10, left: -25, bottom: 5 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="#EDE7DA" />
                <XAxis dataKey="sector" stroke="#817B70" fontSize={10} tickLine={false} />
                <YAxis stroke="#817B70" fontSize={11} tickLine={false} />
                <Tooltip 
                  contentStyle={{ 
                    backgroundColor: '#FCFBF7', 
                    borderColor: '#DCD6CA', 
                    borderRadius: '8px',
                    fontSize: '12px' 
                  }} 
                />
                <Bar dataKey="count" fill="#35483A" radius={[4, 4, 0, 0]} barSize={32} />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>

        {/* Operational Intelligence Summary */}
        <div className="lg:col-span-5 bg-surface border border-border-warm rounded-xl p-5 shadow-subtle flex flex-col justify-between space-y-4">
          <div>
            <h3 className="font-serif text-lg font-semibold text-charcoal">
              Risk Summary & Observations
            </h3>
            <p className="text-xs text-charcoal-muted mt-0.5">
              Automated monthly corridor safety assessment.
            </p>
          </div>

          <div className="space-y-3 text-xs text-charcoal">
            <div className="p-3 rounded-lg bg-cream-light border border-border-warm space-y-1">
              <span className="font-semibold text-accent-forest block font-mono">PEAK RISK WINDOW</span>
              <p className="text-charcoal-muted leading-relaxed">
                Highest bovine activity detected between <strong>14:00 – 16:00 IST</strong> near NH-44 Sector 03 median gap.
              </p>
            </div>

            <div className="p-3 rounded-lg bg-cream-light border border-border-warm space-y-1">
              <span className="font-semibold text-accent-olive block font-mono">RECOMMENDED ACTION</span>
              <p className="text-charcoal-muted leading-relaxed">
                Deploy secondary solar alert signs at KM 142.4 and notify Gram Panchayat warden for animal retrieval.
              </p>
            </div>
          </div>

          <div className="pt-3 border-t border-border-subtle text-[11px] font-mono text-charcoal-subtle flex items-center justify-between">
            <span>Model: GauVision v3.2</span>
            <span>Accuracy: 94.8%</span>
          </div>
        </div>
      </div>
    </div>
  );
};

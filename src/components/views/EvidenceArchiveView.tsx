import React, { useState } from 'react';
import { EvidenceEnvelope } from '../../data/mockData';
import { StatusBadge } from '../common/StatusBadge';
import { FileCheck2, Search, Filter, Download } from 'lucide-react';

interface EvidenceArchiveViewProps {
  envelopes: EvidenceEnvelope[];
  onOpenEnvelope: (envelope: EvidenceEnvelope) => void;
}

export const EvidenceArchiveView: React.FC<EvidenceArchiveViewProps> = ({
  envelopes,
  onOpenEnvelope
}) => {
  const [searchTerm, setSearchTerm] = useState('');
  const [statusFilter, setStatusFilter] = useState('all');

  const filtered = envelopes.filter(ev => {
    const matchesSearch = ev.incidentNo.toLowerCase().includes(searchTerm.toLowerCase()) ||
      ev.cameraName.toLowerCase().includes(searchTerm.toLowerCase()) ||
      ev.animalType.toLowerCase().includes(searchTerm.toLowerCase()) ||
      ev.location.toLowerCase().includes(searchTerm.toLowerCase());
    
    const matchesStatus = statusFilter === 'all' || ev.status.toLowerCase().replace(' ', '_') === statusFilter;
    return matchesSearch && matchesStatus;
  });

  return (
    <div className="space-y-6 pb-12">
      {/* Header */}
      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4 pb-4 border-b border-border-warm">
        <div>
          <h1 className="text-2xl font-serif font-extrabold text-charcoal tracking-tight">
            Evidence Envelope Archive
          </h1>
          <p className="text-xs text-charcoal font-medium mt-0.5">
            Cryptographically logged frame captures, video telemetry, and government incident records.
          </p>
        </div>

        <div className="flex items-center gap-3">
          <button className="px-4 py-2 rounded-lg bg-surface border border-border-warm text-xs font-bold text-charcoal hover:bg-beige/60 transition-colors flex items-center gap-2 shadow-subtle">
            <Download className="w-4 h-4 text-accent-olive" />
            <span>Export Evidence Log (.CSV)</span>
          </button>
        </div>
      </div>

      {/* Filter and Search Bar */}
      <div className="flex flex-col sm:flex-row items-center justify-between gap-4 bg-surface p-4 rounded-xl border border-border-warm shadow-card">
        <div className="relative w-full sm:w-80">
          <Search className="w-4 h-4 text-charcoal-muted absolute left-3 top-2.5" />
          <input
            type="text"
            placeholder="Search incident #, camera, location, or animal..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            className="w-full pl-9 pr-4 py-2 bg-cream border border-border-warm rounded-lg text-xs font-semibold text-charcoal focus:outline-none focus:border-accent-olive"
          />
        </div>

        <div className="flex items-center gap-3 w-full sm:w-auto">
          <div className="flex items-center gap-2 text-xs">
            <Filter className="w-3.5 h-3.5 text-charcoal-subtle" />
            <select
              value={statusFilter}
              onChange={(e) => setStatusFilter(e.target.value)}
              className="bg-cream text-charcoal border border-border-warm px-3.5 py-2 rounded-lg text-xs font-bold shadow-subtle"
            >
              <option value="all">All Statuses</option>
              <option value="open">Open</option>
              <option value="reviewed">Reviewed</option>
              <option value="patrol_dispatched">Patrol Dispatched</option>
              <option value="resolved">Resolved</option>
            </select>
          </div>
        </div>
      </div>

      {/* Evidence Table */}
      <div className="bg-surface border border-border-warm rounded-xl shadow-card overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs text-charcoal border-collapse">
            <thead>
              <tr className="bg-cream-dark border-b border-border-warm text-[11px] font-extrabold text-charcoal-muted uppercase tracking-wider font-sans">
                <th className="py-4 px-5">Incident / Time</th>
                <th className="py-4 px-4">Camera & Location</th>
                <th className="py-4 px-4">Detection Subject</th>
                <th className="py-4 px-4">Confidence</th>
                <th className="py-4 px-4">Severity Tier</th>
                <th className="py-4 px-4">Status</th>
                <th className="py-4 px-5 text-right">Evidence Action</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-border-warm/60">
              {filtered.map((ev) => (
                <tr key={ev.id} className="hover:bg-tint-olive/30 transition-colors group">
                  <td className="py-4.5 px-5">
                    <div className="font-mono font-extrabold text-charcoal text-sm">{ev.incidentNo}</div>
                    <div className="text-xs text-charcoal-muted font-mono mt-0.5">{ev.timestamp}</div>
                  </td>

                  <td className="py-4.5 px-4">
                    <div className="font-extrabold text-charcoal font-sans">{ev.cameraName.split(' - ')[0]}</div>
                    <div className="text-xs text-charcoal font-medium mt-0.5">{ev.location}</div>
                  </td>

                  <td className="py-4.5 px-4">
                    <div className="font-bold text-charcoal">{ev.animalType}</div>
                    <div className="text-xs text-charcoal-muted font-medium">{ev.count} head detected</div>
                  </td>

                  <td className="py-4.5 px-4 font-mono font-extrabold text-accent-olive text-sm">
                    {ev.confidence}%
                  </td>

                  <td className="py-4.5 px-4">
                    <StatusBadge status={ev.severity} size="sm" />
                  </td>

                  <td className="py-4.5 px-4">
                    <StatusBadge status={ev.status} size="sm" />
                  </td>

                  <td className="py-4.5 px-5 text-right">
                    <button
                      onClick={() => onOpenEnvelope(ev)}
                      className="inline-flex items-center gap-2 px-3.5 py-2 rounded-lg bg-tint-olive hover:bg-tint-olive/80 border border-tint-olive-border font-extrabold text-xs text-tint-olive-text transition-colors shadow-subtle"
                    >
                      <FileCheck2 className="w-4 h-4 text-accent-olive" />
                      <span>Inspect Envelope</span>
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
};

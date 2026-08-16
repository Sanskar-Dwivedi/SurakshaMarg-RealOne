import React, { useState } from 'react';
import { Settings, Save, Bell, Shield, Sliders, CheckCircle2 } from 'lucide-react';

export const SettingsView: React.FC = () => {
  const [confidenceThreshold, setConfidenceThreshold] = useState(85);
  const [autoEscalateMins, setAutoEscalateMins] = useState(3);
  const [vmsWarningEnabled, setVmsWarningEnabled] = useState(true);
  const [savedSuccess, setSavedSuccess] = useState(false);

  const handleSave = () => {
    setSavedSuccess(true);
    setTimeout(() => setSavedSuccess(false), 3000);
  };

  return (
    <div className="space-y-6 pb-12 max-w-4xl">
      {/* Header */}
      <div className="flex items-center justify-between pb-4 border-b border-border-warm">
        <div>
          <h1 className="text-2xl font-serif font-bold text-charcoal tracking-tight">
            System Parameters & Configuration
          </h1>
          <p className="text-xs text-charcoal-muted mt-0.5">
            GauVision AI detection sensitivity, alert dispatch parameters, and compliance rules.
          </p>
        </div>

        <button
          onClick={handleSave}
          className="px-4 py-2 rounded-lg bg-accent-olive text-cream hover:bg-accent-forest font-semibold text-xs transition-colors shadow-subtle flex items-center gap-2"
        >
          <Save className="w-3.5 h-3.5 text-accent-sand" />
          <span>Save Configuration</span>
        </button>
      </div>

      {savedSuccess && (
        <div className="p-3 rounded-lg bg-accent-olive/15 text-accent-olive border border-accent-olive/30 text-xs font-mono flex items-center gap-2 animate-fadeIn">
          <CheckCircle2 className="w-4 h-4 text-accent-olive" />
          <span>System parameters updated and synchronized across all 20 edge camera nodes.</span>
        </div>
      )}

      {/* Model Sensitivity Section */}
      <div className="bg-surface border border-border-warm rounded-xl p-5 shadow-subtle space-y-4">
        <div className="flex items-center gap-2 pb-3 border-b border-border-subtle">
          <Sliders className="w-4 h-4 text-accent-olive" />
          <h3 className="font-serif text-lg font-semibold text-charcoal">
            GauVision Computer Vision Sensitivity
          </h3>
        </div>

        <div className="space-y-4 text-xs">
          <div>
            <div className="flex items-center justify-between mb-1">
              <label className="font-semibold text-charcoal">Minimum Confidence Threshold ({confidenceThreshold}%)</label>
              <span className="font-mono text-charcoal-muted">Filter out false-positive bounding triggers</span>
            </div>
            <input
              type="range"
              min="60"
              max="98"
              value={confidenceThreshold}
              onChange={(e) => setConfidenceThreshold(Number(e.target.value))}
              className="w-full accent-accent-olive cursor-pointer"
            />
            <p className="text-charcoal-muted mt-1">Detections with confidence below {confidenceThreshold}% will be archived without raising urgent control room alarms.</p>
          </div>
        </div>
      </div>

      {/* Alert Escalation Section */}
      <div className="bg-surface border border-border-warm rounded-xl p-5 shadow-subtle space-y-4">
        <div className="flex items-center gap-2 pb-3 border-b border-border-subtle">
          <Bell className="w-4 h-4 text-status-critical" />
          <h3 className="font-serif text-lg font-semibold text-charcoal">
            Incident Dispatch & Escalation Rules
          </h3>
        </div>

        <div className="space-y-4 text-xs">
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <div>
              <label className="font-semibold text-charcoal block mb-1">Auto-Escalation Delay (Minutes)</label>
              <input
                type="number"
                value={autoEscalateMins}
                onChange={(e) => setAutoEscalateMins(Number(e.target.value))}
                className="w-full p-2 bg-cream-light border border-border-warm rounded-lg text-xs font-mono text-charcoal"
              />
            </div>

            <div className="flex items-center justify-between pt-5">
              <div>
                <label className="font-semibold text-charcoal block">Variable Message Sign (VMS) Trigger</label>
                <span className="text-charcoal-muted text-[11px]">Automatically display "ANIMAL AHEAD" on highway LED signs</span>
              </div>
              <input
                type="checkbox"
                checked={vmsWarningEnabled}
                onChange={(e) => setVmsWarningEnabled(e.target.checked)}
                className="w-4 h-4 accent-accent-olive cursor-pointer"
              />
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

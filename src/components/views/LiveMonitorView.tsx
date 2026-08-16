import React, { useState } from 'react';
import { Camera, Detection } from '../../data/mockData';
import { CameraFeed } from '../dashboard/CameraFeed';
import { Grid, LayoutGrid, Square, Filter } from 'lucide-react';
import { clsx } from 'clsx';

interface LiveMonitorViewProps {
  cameras: Camera[];
  selectedCamera: Camera;
  onSelectCamera: (cam: Camera) => void;
  detections: Detection[];
  onReviewIncident: (incidentNo: string) => void;
}

export const LiveMonitorView: React.FC<LiveMonitorViewProps> = ({
  cameras,
  selectedCamera,
  onSelectCamera,
  detections,
  onReviewIncident
}) => {
  const [gridMode, setGridMode] = useState<'1x1' | '2x2' | '3x3'>('2x2');
  const [filterSector, setFilterSector] = useState<string>('all');

  const filteredCameras = cameras.filter(c => filterSector === 'all' || c.sector.includes(filterSector));

  return (
    <div className="space-y-6 pb-12">
      {/* Header controls */}
      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4 pb-4 border-b border-border-warm">
        <div>
          <h1 className="text-2xl font-serif font-bold text-charcoal tracking-tight">
            Live Camera Monitor Array
          </h1>
          <p className="text-xs text-charcoal-muted mt-0.5">
            Multi-stream highway surveillance grid for simultaneous sector monitoring.
          </p>
        </div>

        <div className="flex items-center gap-4">
          {/* Sector Filter */}
          <div className="flex items-center gap-2 text-xs">
            <Filter className="w-3.5 h-3.5 text-charcoal-subtle" />
            <select
              value={filterSector}
              onChange={(e) => setFilterSector(e.target.value)}
              className="bg-surface text-charcoal border border-border-warm px-3 py-1.5 rounded-lg text-xs font-medium"
            >
              <option value="all">All Sectors (NH-44 & Corridors)</option>
              <option value="Sector 01">Sector 01 - Toll North</option>
              <option value="Sector 02">Sector 02 - State Hwy 12</option>
              <option value="Sector 03">Sector 03 - Median Hotspot</option>
              <option value="Sector 05">Sector 05 - Ring Road</option>
            </select>
          </div>

          {/* Grid Layout Selector */}
          <div className="flex items-center gap-1 bg-cream-dark p-1 rounded-lg border border-border-warm text-xs">
            <button
              onClick={() => setGridMode('1x1')}
              className={clsx(
                'p-1.5 rounded transition-colors',
                gridMode === '1x1' ? 'bg-surface text-charcoal shadow-subtle' : 'text-charcoal-subtle hover:text-charcoal'
              )}
              title="Single Featured Stream"
            >
              <Square className="w-4 h-4" />
            </button>
            <button
              onClick={() => setGridMode('2x2')}
              className={clsx(
                'p-1.5 rounded transition-colors',
                gridMode === '2x2' ? 'bg-surface text-charcoal shadow-subtle' : 'text-charcoal-subtle hover:text-charcoal'
              )}
              title="2x2 Multi Grid"
            >
              <Grid className="w-4 h-4" />
            </button>
            <button
              onClick={() => setGridMode('3x3')}
              className={clsx(
                'p-1.5 rounded transition-colors',
                gridMode === '3x3' ? 'bg-surface text-charcoal shadow-subtle' : 'text-charcoal-subtle hover:text-charcoal'
              )}
              title="3x3 Stream Matrix"
            >
              <LayoutGrid className="w-4 h-4" />
            </button>
          </div>
        </div>
      </div>

      {/* Grid Layout Matrix */}
      <div className={clsx(
        'grid gap-6',
        gridMode === '1x1' ? 'grid-cols-1' :
        gridMode === '2x2' ? 'grid-cols-1 md:grid-cols-2' :
        'grid-cols-1 sm:grid-cols-2 lg:grid-cols-3'
      )}>
        {filteredCameras.map((cam) => {
          const camBoxes = detections.find(d => d.cameraId === cam.id)?.boundingBoxes || [];
          return (
            <div key={cam.id} className="flex flex-col">
              <CameraFeed
                camera={cam}
                allCameras={cameras}
                onSelectCamera={onSelectCamera}
                boundingBoxes={camBoxes}
                onOpenIncident={onReviewIncident}
              />
            </div>
          );
        })}
      </div>
    </div>
  );
};

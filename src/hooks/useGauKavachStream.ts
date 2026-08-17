import { useState, useEffect, useCallback, useRef } from 'react';

export interface BackendBBox {
  x: number;
  y: number;
  width: number;
  height: number;
}

export interface BackendBBoxPct {
  x: number;
  y: number;
  w: number;
  h: number;
}

export interface BackendDetection {
  id: string;
  track_id: number;
  class: string;
  label: string;
  confidence: number;
  severity: 'high_risk' | 'monitored';
  confirmed: boolean;
  on_road: boolean;
  speaker_id: string | null;
  bbox: BackendBBox;
  bbox_pct: BackendBBoxPct;
}

export interface BackendCamera {
  id: string;
  name: string;
  code: string;
  location: string;
  sector: string;
  status: string;
  fps: number;
  latencyMs: number;
  coords: { x: number; y: number; lat: number; lng: number };
  modelVersion: string;
  detectionsToday?: number;
  lastActive?: string;
  uptimePct?: number;
  signalDb?: number;
  ipAddress?: string;
}

export interface BackendIncident {
  id: string;
  incidentNo: string;
  timestamp: string;
  cameraId: string;
  cameraName: string;
  location: string;
  sector: string;
  species: string;
  confidence: number;
  severity: 'high_risk' | 'medium_risk' | 'resolved';
  status: 'active' | 'resolved' | 'investigating';
  speakerId: string;
  actionTaken: string;
  ledgerVerified: boolean;
}

export interface TelemetryData {
  type: string;
  timestamp: string;
  frame_id: number;
  fps: number;
  latency_ms: number;
  status: 'CONNECTING' | 'ONLINE' | 'DEGRADED' | 'OFFLINE' | 'ERROR';
  camera: BackendCamera;
  total_animals_detected: number;
  detections: BackendDetection[];
  incidents: BackendIncident[];
  ledger_valid: boolean;
  hardware_activated: boolean;
}

const DEFAULT_CAMERA: BackendCamera = {
  id: 'cam-07',
  name: 'CAM07 — NH-44 · Median Crossing Sector 03',
  code: 'CAM-07',
  location: 'NH-44 · Sector 03 (Median Crossing)',
  sector: 'Sector 03',
  status: 'connecting',
  fps: 0,
  latencyMs: 0,
  coords: { x: 42, y: 68, lat: 28.4989, lng: 77.3420 },
  modelVersion: 'GauVision v0.5 YOLO',
  detectionsToday: 0,
};

export function useGauKavachStream(wsUrl: string = 'ws://localhost:8000/ws', httpUrl: string = 'http://localhost:8000') {
  const [connectionStatus, setConnectionStatus] = useState<'CONNECTING' | 'ONLINE' | 'DEGRADED' | 'OFFLINE' | 'ERROR'>('CONNECTING');
  const [telemetry, setTelemetry] = useState<TelemetryData | null>(null);
  const wsRef = useRef<WebSocket | null>(null);
  const reconnectTimer = useRef<NodeJS.Timeout | null>(null);

  const connect = useCallback(() => {
    try {
      setConnectionStatus('CONNECTING');
      const ws = new WebSocket(wsUrl);
      wsRef.current = ws;

      ws.onopen = () => {
        setConnectionStatus('ONLINE');
        if (reconnectTimer.current) {
          clearTimeout(reconnectTimer.current);
          reconnectTimer.current = null;
        }
      };

      ws.onmessage = (event) => {
        try {
          const data: TelemetryData = JSON.parse(event.data);
          setTelemetry(data);
          setConnectionStatus(data.status || 'ONLINE');
        } catch (err) {
          console.error('[GauKavach WS] Error parsing telemetry message:', err);
        }
      };

      ws.onerror = () => {
        setConnectionStatus('ERROR');
      };

      ws.onclose = () => {
        setConnectionStatus('OFFLINE');
        reconnectTimer.current = setTimeout(() => {
          connect();
        }, 3000);
      };
    } catch (err) {
      setConnectionStatus('OFFLINE');
      reconnectTimer.current = setTimeout(() => {
        connect();
      }, 3000);
    }
  }, [wsUrl]);

  useEffect(() => {
    connect();
    return () => {
      if (wsRef.current) {
        wsRef.current.close();
      }
      if (reconnectTimer.current) {
        clearTimeout(reconnectTimer.current);
      }
    };
  }, [connect]);

  const takeSnapshot = async () => {
    try {
      const res = await fetch(`${httpUrl}/api/snapshot`, { method: 'POST' });
      if (!res.ok) throw new Error('Snapshot API error');
      const data = await res.json();
      return data;
    } catch (err) {
      console.error('[GauKavach API] Snapshot request failed:', err);
      return null;
    }
  };

  const getStreamUrl = (camId?: string) => {
    const id = camId || telemetry?.camera?.id || 'cam-07';
    return `${httpUrl}/api/stream/${id}`;
  };

  return {
    connectionStatus,
    telemetry,
    camera: telemetry?.camera || DEFAULT_CAMERA,
    fps: telemetry?.fps || 0,
    latencyMs: telemetry?.latency_ms || 0,
    animalCount: telemetry?.total_animals_detected || 0,
    detections: telemetry?.detections || [],
    incidents: telemetry?.incidents || [],
    ledgerValid: telemetry?.ledger_valid ?? true,
    takeSnapshot,
    streamUrl: `${httpUrl}/api/stream/${telemetry?.camera?.id || 'cam-07'}`,
    getStreamUrl,
  };
}

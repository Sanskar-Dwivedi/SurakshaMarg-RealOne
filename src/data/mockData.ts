export interface Camera {
  id: string;
  name: string;
  code: string;
  sector: string;
  location: string;
  status: 'online' | 'attention' | 'offline';
  fps: number;
  latencyMs: number;
  uptimePct: number;
  detectionsToday: number;
  lastActive: string;
  signalDb: number;
  ipAddress: string;
  coords: { x: number; y: number; lat: number; lng: number };
  modelVersion: string;
}

export interface BoundingBox {
  id: string;
  label: string;
  confidence: number;
  severity: 'normal' | 'caution' | 'high_risk';
  x: number; // percentage
  y: number; // percentage
  w: number; // percentage
  h: number; // percentage
}

export interface Detection {
  id: string;
  incidentNo: string;
  timestamp: string;
  timeAgo: string;
  cameraId: string;
  cameraName: string;
  location: string;
  sector: string;
  animalType: string;
  animalCount: number;
  confidence: number;
  severity: 'normal' | 'caution' | 'high_risk';
  roadRiskLevel: 'Low' | 'Moderate' | 'High' | 'Severe';
  status: 'Open' | 'Under Review' | 'Patrol Dispatched' | 'Resolved';
  evidenceId: string;
  boundingBoxes: BoundingBox[];
}

export interface AlertItem {
  id: string;
  incidentNo: string;
  title: string;
  location: string;
  cameraId: string;
  sector: string;
  timestamp: string;
  timeAgo: string;
  severity: 'critical' | 'attention' | 'monitoring';
  animalType: string;
  distanceToCarriagewayMeters: number;
  recommendedAction: string;
}

export interface EvidenceEnvelope {
  id: string;
  incidentNo: string;
  timestamp: string;
  cameraId: string;
  cameraName: string;
  sector: string;
  location: string;
  animalType: string;
  count: number;
  confidence: number;
  severity: 'normal' | 'caution' | 'high_risk';
  status: 'Open' | 'Reviewed' | 'Patrol Dispatched' | 'Resolved';
  frameImage: string;
  videoDurationSec: number;
  speedLimitKmh: number;
  estRoadOccupancySec: number;
  weatherCondition: string;
  lightCondition: string;
  operatorNotes?: string;
  auditTrail: {
    time: string;
    action: string;
    actor: string;
    notes: string;
  }[];
}

export const MOCK_CAMERAS: Camera[] = [
  {
    id: 'cam-01',
    name: 'CAM 01',
    code: 'NH44-SEC01-N',
    sector: 'Sector 01',
    location: 'NH-44 · Toll Plaza North',
    status: 'online',
    fps: 30,
    latencyMs: 42,
    uptimePct: 99.8,
    detectionsToday: 4,
    lastActive: 'Just now',
    signalDb: -62,
    ipAddress: '192.168.14.101',
    coords: { x: 18, y: 28, lat: 28.5355, lng: 77.2410 },
    modelVersion: 'GauVision v3.2'
  },
  {
    id: 'cam-02',
    name: 'CAM 02',
    code: 'NH44-SEC01-S',
    sector: 'Sector 01',
    location: 'NH-44 · Flyover Interchange',
    status: 'online',
    fps: 30,
    latencyMs: 38,
    uptimePct: 99.4,
    detectionsToday: 2,
    lastActive: '1 min ago',
    signalDb: -68,
    ipAddress: '192.168.14.102',
    coords: { x: 28, y: 36, lat: 28.5210, lng: 77.2580 },
    modelVersion: 'GauVision v3.2'
  },
  {
    id: 'cam-03',
    name: 'CAM 03',
    code: 'SH12-SEC02-W',
    sector: 'Sector 02',
    location: 'State Hwy 12 · Canal Bridge',
    status: 'attention',
    fps: 18,
    latencyMs: 140,
    uptimePct: 94.1,
    detectionsToday: 6,
    lastActive: '3 mins ago',
    signalDb: -84,
    ipAddress: '192.168.14.103',
    coords: { x: 42, y: 24, lat: 28.5490, lng: 77.2910 },
    modelVersion: 'GauVision v3.1'
  },
  {
    id: 'cam-04',
    name: 'CAM 04',
    code: 'SH12-SEC02-E',
    sector: 'Sector 02',
    location: 'State Hwy 12 · Agricultural Corridor',
    status: 'online',
    fps: 30,
    latencyMs: 45,
    uptimePct: 99.1,
    detectionsToday: 3,
    lastActive: '4 mins ago',
    signalDb: -70,
    ipAddress: '192.168.14.104',
    coords: { x: 55, y: 32, lat: 28.5380, lng: 77.3150 },
    modelVersion: 'GauVision v3.2'
  },
  {
    id: 'cam-07',
    name: 'CAM 07',
    code: 'NH44-SEC03-C',
    sector: 'Sector 03',
    location: 'NH-44 · Median Crossing Sector 03',
    status: 'online',
    fps: 30,
    latencyMs: 34,
    uptimePct: 100.0,
    detectionsToday: 8,
    lastActive: 'Live',
    signalDb: -58,
    ipAddress: '192.168.14.107',
    coords: { x: 68, y: 52, lat: 28.4980, lng: 77.3420 },
    modelVersion: 'GauVision v3.2-HQ'
  },
  {
    id: 'cam-11',
    name: 'CAM 11',
    code: 'RING-SEC05-N',
    sector: 'Sector 05',
    location: 'Outer Ring Road · Expressway Curve',
    status: 'online',
    fps: 29,
    latencyMs: 48,
    uptimePct: 98.7,
    detectionsToday: 4,
    lastActive: '8 mins ago',
    signalDb: -72,
    ipAddress: '192.168.14.111',
    coords: { x: 34, y: 64, lat: 28.4720, lng: 77.2790 },
    modelVersion: 'GauVision v3.2'
  },
  {
    id: 'cam-14',
    name: 'CAM 14',
    code: 'NH44-SEC06-W',
    sector: 'Sector 06',
    location: 'NH-44 · Livestock Movement Corridor',
    status: 'offline',
    fps: 0,
    latencyMs: 0,
    uptimePct: 82.3,
    detectionsToday: 0,
    lastActive: '42 mins ago',
    signalDb: -99,
    ipAddress: '192.168.14.114',
    coords: { x: 78, y: 72, lat: 28.4410, lng: 77.3890 },
    modelVersion: 'GauVision v3.0'
  },
  {
    id: 'cam-18',
    name: 'CAM 18',
    code: 'EXP-SEC08-E',
    sector: 'Sector 08',
    location: 'Yamuna Link Expressway · Entry Ramp',
    status: 'online',
    fps: 30,
    latencyMs: 36,
    uptimePct: 99.9,
    detectionsToday: 0,
    lastActive: '12 mins ago',
    signalDb: -64,
    ipAddress: '192.168.14.118',
    coords: { x: 88, y: 44, lat: 28.5120, lng: 77.4120 },
    modelVersion: 'GauVision v3.2'
  }
];

export const MOCK_DETECTIONS: Detection[] = [
  {
    id: 'det-101',
    incidentNo: 'GV-0248',
    timestamp: '15:18:42 IST',
    timeAgo: '2 min ago',
    cameraId: 'cam-07',
    cameraName: 'CAM 07',
    location: 'NH-44 · Sector 03',
    sector: 'Sector 03',
    animalType: 'Cattle (Bovine)',
    animalCount: 2,
    confidence: 94.8,
    severity: 'high_risk',
    roadRiskLevel: 'Severe',
    status: 'Open',
    evidenceId: 'EV-0248',
    boundingBoxes: [
      { id: 'b1', label: 'CATTLE', confidence: 94.8, severity: 'high_risk', x: 42, y: 38, w: 26, h: 32 },
      { id: 'b2', label: 'CALF', confidence: 88.2, severity: 'caution', x: 28, y: 48, w: 14, h: 22 }
    ]
  },
  {
    id: 'det-102',
    incidentNo: 'GV-0247',
    timestamp: '15:12:10 IST',
    timeAgo: '8 min ago',
    cameraId: 'cam-04',
    cameraName: 'CAM 04',
    location: 'State Hwy 12 · Agricultural Corridor',
    sector: 'Sector 02',
    animalType: 'Cattle',
    animalCount: 1,
    confidence: 91.5,
    severity: 'caution',
    roadRiskLevel: 'Moderate',
    status: 'Under Review',
    evidenceId: 'EV-0247',
    boundingBoxes: [
      { id: 'b3', label: 'CATTLE', confidence: 91.5, severity: 'caution', x: 62, y: 44, w: 22, h: 28 }
    ]
  },
  {
    id: 'det-103',
    incidentNo: 'GV-0246',
    timestamp: '14:58:33 IST',
    timeAgo: '22 min ago',
    cameraId: 'cam-11',
    cameraName: 'CAM 11',
    location: 'Outer Ring Road · Expressway Curve',
    sector: 'Sector 05',
    animalType: 'Nilgai (Blue Bull)',
    animalCount: 1,
    confidence: 89.1,
    severity: 'high_risk',
    roadRiskLevel: 'High',
    status: 'Patrol Dispatched',
    evidenceId: 'EV-0246',
    boundingBoxes: [
      { id: 'b4', label: 'NILGAI', confidence: 89.1, severity: 'high_risk', x: 50, y: 40, w: 28, h: 34 }
    ]
  },
  {
    id: 'det-104',
    incidentNo: 'GV-0245',
    timestamp: '14:43:05 IST',
    timeAgo: '37 min ago',
    cameraId: 'cam-01',
    cameraName: 'CAM 01',
    location: 'NH-44 · Toll Plaza North',
    sector: 'Sector 01',
    animalType: 'Stray Canines (Pack)',
    animalCount: 3,
    confidence: 96.2,
    severity: 'normal',
    roadRiskLevel: 'Low',
    status: 'Resolved',
    evidenceId: 'EV-0245',
    boundingBoxes: [
      { id: 'b5', label: 'CANINE', confidence: 96.2, severity: 'normal', x: 18, y: 60, w: 12, h: 16 }
    ]
  },
  {
    id: 'det-105',
    incidentNo: 'GV-0244',
    timestamp: '14:15:20 IST',
    timeAgo: '1 hr ago',
    cameraId: 'cam-03',
    cameraName: 'CAM 03',
    location: 'State Hwy 12 · Canal Bridge',
    sector: 'Sector 02',
    animalType: 'Cattle',
    animalCount: 2,
    confidence: 93.4,
    severity: 'caution',
    roadRiskLevel: 'Moderate',
    status: 'Resolved',
    evidenceId: 'EV-0244',
    boundingBoxes: [
      { id: 'b6', label: 'CATTLE', confidence: 93.4, severity: 'caution', x: 35, y: 52, w: 24, h: 30 }
    ]
  }
];

export const MOCK_ALERTS: AlertItem[] = [
  {
    id: 'alt-01',
    incidentNo: 'GV-0248',
    title: 'Cattle detected near active carriageway',
    location: 'NH-44 · Sector 03',
    cameraId: 'CAM 07',
    sector: 'Sector 03',
    timestamp: '15:18:42 IST',
    timeAgo: '2 min ago',
    severity: 'critical',
    animalType: 'Cattle (2 heads)',
    distanceToCarriagewayMeters: 1.8,
    recommendedAction: 'Dispatch Highway Patrol Unit 04 & activate VMS warning sign'
  },
  {
    id: 'alt-02',
    incidentNo: 'GV-0246',
    title: 'High-speed wildlife highway entry',
    location: 'Outer Ring Road · Sector 05',
    cameraId: 'CAM 11',
    sector: 'Sector 05',
    timestamp: '14:58:33 IST',
    timeAgo: '22 min ago',
    severity: 'critical',
    animalType: 'Nilgai (Large adult male)',
    distanceToCarriagewayMeters: 0.5,
    recommendedAction: 'Alert Sector 05 Rapid Response Patrol'
  },
  {
    id: 'alt-03',
    incidentNo: 'GV-0247',
    title: 'Stray bovine grazing near shoulder lane',
    location: 'State Hwy 12 · Sector 02',
    cameraId: 'CAM 04',
    sector: 'Sector 02',
    timestamp: '15:12:10 IST',
    timeAgo: '8 min ago',
    severity: 'attention',
    animalType: 'Cattle (Single)',
    distanceToCarriagewayMeters: 4.2,
    recommendedAction: 'Monitor movement vector; inform local Gram Panchayat warden'
  }
];

export const MOCK_EVIDENCE_ENVELOPES: EvidenceEnvelope[] = [
  {
    id: 'EV-0248',
    incidentNo: 'GV-0248',
    timestamp: '15:18:42 IST (15 Aug 2026)',
    cameraId: 'cam-07',
    cameraName: 'CAM 07 - NH44-SEC03-C',
    sector: 'Sector 03 · National Highway 44',
    location: 'KM 142.4 · Northbound Carriageway',
    animalType: 'Bovine Cattle (Adult + Calf)',
    count: 2,
    confidence: 94.8,
    severity: 'high_risk',
    status: 'Open',
    frameImage: '/assets/evidence/cam07_frame.jpg',
    videoDurationSec: 15,
    speedLimitKmh: 80,
    estRoadOccupancySec: 140,
    weatherCondition: 'Clear · Day Vision',
    lightCondition: 'Daylight (Sun angle 42°)',
    operatorNotes: 'Cattle entered carriageway from eastern agricultural buffer zone. High collision risk for fast lane traffic.',
    auditTrail: [
      { time: '15:18:42', action: 'System Detection', actor: 'GauVision Engine v3.2', notes: 'Automated bounding box trigger (94.8% confidence).' },
      { time: '15:19:05', action: 'Alert Raised', actor: 'Central Dispatch System', notes: 'Dispatched notification to Highway Control Room.' },
      { time: '15:19:30', action: 'Operator Acknowledged', actor: 'Officer S. Sharma (ID: 482)', notes: 'Verified visual feed. Initiated patrol request.' }
    ]
  },
  {
    id: 'EV-0247',
    incidentNo: 'GV-0247',
    timestamp: '15:12:10 IST (15 Aug 2026)',
    cameraId: 'cam-04',
    cameraName: 'CAM 04 - SH12-SEC02-E',
    sector: 'Sector 02 · State Highway 12',
    location: 'KM 28.1 · Eastbound Lane',
    animalType: 'Bovine Cattle',
    count: 1,
    confidence: 91.5,
    severity: 'caution',
    status: 'Reviewed',
    frameImage: '/assets/evidence/cam04_frame.jpg',
    videoDurationSec: 10,
    speedLimitKmh: 65,
    estRoadOccupancySec: 45,
    weatherCondition: 'Partly Cloudy',
    lightCondition: 'Daylight',
    operatorNotes: 'Single cow grazing within 4m of asphalt edge. Vehicle speed reduced via VMS advisory.',
    auditTrail: [
      { time: '15:12:10', action: 'System Detection', actor: 'GauVision Engine v3.2', notes: 'Automated detection trigger.' },
      { time: '15:14:00', action: 'Reviewed & Flagged', actor: 'Operator M. Verma (ID: 109)', notes: 'Marked under observation.' }
    ]
  },
  {
    id: 'EV-0246',
    incidentNo: 'GV-0246',
    timestamp: '14:58:33 IST (15 Aug 2026)',
    cameraId: 'cam-11',
    cameraName: 'CAM 11 - RING-SEC05-N',
    sector: 'Sector 05 · Outer Ring Road',
    location: 'KM 08.6 · Expressway Bypass',
    animalType: 'Nilgai (Blue Bull)',
    count: 1,
    confidence: 89.1,
    severity: 'high_risk',
    status: 'Patrol Dispatched',
    frameImage: '/assets/evidence/cam11_frame.jpg',
    videoDurationSec: 20,
    speedLimitKmh: 90,
    estRoadOccupancySec: 210,
    weatherCondition: 'Clear',
    lightCondition: 'Daylight',
    operatorNotes: 'Large Nilgai crossed central barrier gap. Highway Patrol Unit 09 dispatched for safety interception.',
    auditTrail: [
      { time: '14:58:33', action: 'System Detection', actor: 'GauVision Engine v3.2', notes: 'High severity wildlife detection.' },
      { time: '15:01:10', action: 'Patrol Dispatched', actor: 'Control Room Officer R. Singh', notes: 'Patrol Van 09 dispatched from Sector 05 station.' }
    ]
  }
];

export const HOURLY_DETECTION_STATS = [
  { hour: '06:00', detections: 2, highRisk: 0, cattle: 2, wildlife: 0 },
  { hour: '08:00', detections: 5, highRisk: 1, cattle: 4, wildlife: 1 },
  { hour: '10:00', detections: 7, highRisk: 1, cattle: 6, wildlife: 1 },
  { hour: '12:00', detections: 4, highRisk: 0, cattle: 3, wildlife: 1 },
  { hour: '14:00', detections: 6, highRisk: 2, cattle: 5, wildlife: 1 },
  { hour: '15:00', detections: 3, highRisk: 1, cattle: 2, wildlife: 1 },
  { hour: '16:00 (Est)', detections: 4, highRisk: 1, cattle: 3, wildlife: 1 },
];

export const CAMERA_SECTOR_STATS = [
  { sector: 'Sector 01 (NH-44)', count: 6, riskRatio: '16.6%', cameras: 2 },
  { sector: 'Sector 02 (SH-12)', count: 9, riskRatio: '22.2%', cameras: 2 },
  { sector: 'Sector 03 (NH-44 High Density)', count: 8, riskRatio: '37.5%', cameras: 3 },
  { sector: 'Sector 05 (Ring Expressway)', count: 4, riskRatio: '50.0%', cameras: 2 },
];

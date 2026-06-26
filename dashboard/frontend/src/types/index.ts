export interface Region {
  id: string;
  name: string;
  lat: number;
  lon: number;
}

export interface DemandPoint {
  time: string;
  demand_mw: number;
}

export interface Prediction {
  created_at: string;
  predictions: number[];
}

export interface AccuracyPoint {
  horizon: number;
  mape: number | null;
}

export interface WSMessage {
  type: 'demand_update' | 'prediction_update';
  timestamp: string;
  region_id: string;
  demand_mw?: number;
  predictions?: number[];
}

export interface GlobalMetrics {
  max_demand: number;
  gradient_max: number;
  vm_metrics: Record<string, number>;
}
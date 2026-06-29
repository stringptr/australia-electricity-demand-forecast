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

export interface InsightDataPoint {
  time?: string;
  date?: string;
  region_id: string;
  region_name: string;
  demand_mw?: number;
  demand_mw_avg?: number;
  demand_mw_min?: number;
  demand_mw_max?: number;
  temperature_2m?: number;
  temperature_2m_avg?: number;
  relative_humidity_2m?: number;
  relative_humidity_avg?: number;
  precipitation?: number;
  precipitation_sum?: number;
  cloud_cover?: number;
  cloud_cover_avg?: number;
  wind_speed_10m?: number;
  wind_speed_10m_avg?: number;
  shortwave_radiation?: number;
  shortwave_radiation_avg?: number;
}

export interface CorrelationResult {
  variable: string;
  variable_label: string;
  r: number | null;
  n: number;
}

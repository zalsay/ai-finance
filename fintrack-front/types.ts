
export type View = 'dashboard' | 'watchlist' | 'pricing' | 'portfolio' | 'news' | 'settings';

export interface StockPrediction {
  predicted_high: number;
  predicted_low: number;
  confidence: number;
  sentiment: 'Bullish' | 'Bearish' | 'Neutral';
  analysis: string;
  chartData?: {
    dates: string[];
    actuals: number[];
    predictions: number[];
  };
}

export interface StockData {
  symbol: string;
  companyName: string;
  currentPrice: number;
  changePercent: number;
  prediction?: StockPrediction;
}

export interface TimesfmBest {
  unique_key: string;
  symbol: string;
  timesfm_version: string;
  best_prediction_item: string;
  best_metrics: string;
  is_public: number;
  short_name?: string;
}

export interface TimesfmChunk {
  unique_key: string;
  chunk_index: number;
  start_date: string;
  end_date: string;
  symbol: string;
  predictions: Record<string, number[]>;
  actual_values: number[];
  dates: string[];
}

export interface PublicPredictionItem {
  best: TimesfmBest;
  chunks: TimesfmChunk[];
}

export interface PublicPredictionResponse {
  items: PublicPredictionItem[];
  count: number;
}

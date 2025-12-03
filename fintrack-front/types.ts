
export type View = 'dashboard' | 'watchlist' | 'pricing' | 'portfolio' | 'news' | 'settings';

export interface StockPrediction {
  predicted_high: number;
  predicted_low: number;
  confidence: number;
  sentiment: 'Bullish' | 'Bearish' | 'Neutral';
  analysis: string;
  modelName?: string;
  contextLen?: number;
  horizonLen?: number;
  chartData?: {
    dates: string[];
    actuals: number[];
    predictions: number[];
  };
  maxDeviationPercent?: number;
}

export interface StockData {
  symbol: string;
  companyName: string;
  currentPrice: number;
  changePercent: number;
  predictedChangePercent?: number;
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
  context_len?: number;
  horizon_len?: number;
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
  max_deviation_percent?: number;
}

export interface PublicPredictionResponse {
  items: PublicPredictionItem[];
  count: number;
}

export interface StrategyParams {
  unique_key: string;
  buy_threshold_pct: number;
  sell_threshold_pct: number;
  initial_cash: number;
  enable_rebalance: boolean;
  max_position_pct: number;
  min_position_pct: number;
  slope_position_per_pct: number;
  rebalance_tolerance_pct: number;
  trade_fee_rate: number;
  take_profit_threshold_pct: number;
  take_profit_sell_frac: number;
  user_id?: number;
}

export interface SaveStrategyParamsRequest extends StrategyParams {}
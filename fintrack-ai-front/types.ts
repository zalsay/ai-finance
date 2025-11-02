
export type View = 'dashboard' | 'watchlist' | 'pricing' | 'portfolio' | 'news' | 'settings';

export interface StockPrediction {
  predicted_high: number;
  predicted_low: number;
  confidence: number;
  sentiment: 'Bullish' | 'Bearish' | 'Neutral';
  analysis: string;
}

export interface StockData {
  symbol: string;
  companyName: string;
  currentPrice: number;
  changePercent: number;
  prediction?: StockPrediction;
}

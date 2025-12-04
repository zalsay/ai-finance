import { PublicPredictionResponse } from '../types';

// API服务 - 连接fintrack-api后端
const DEV_BASE = (import.meta.env as any).VITE_API_BASE_URL_DEV as string | undefined;
const PROD_BASE = (import.meta.env as any).VITE_API_BASE_URL_PROD as string | undefined;
const API_BASE_URL = (import.meta.env as any).DEV
  ? (DEV_BASE || 'http://localhost:59000/api/v1')
  : (PROD_BASE || 'http://go-api.meetlife.com.cn:9000/api/v1');

// 存储认证token
let authToken: string | null = null;

// API响应类型定义
export interface User {
  id: number;
  email: string;
  username: string;
  first_name?: string;
  last_name?: string;
  is_premium: boolean;
  created_at: string;
  updated_at?: string;
}

export interface AuthResponse {
  token: string;
  user: User;
}

export interface WatchlistItem {
  id: number;
  stock: {
    id: number;
    symbol: string;
    company_name: string;
    exchange: string;
    sector: string;
    industry?: string;
    market_cap?: number;
    created_at: string;
    updated_at: string;
  };
  current_price: {
    id: number;
    stock_id: number;
    price: number;
    change_percent: number;
    volume: number;
    market_cap?: number;
    recorded_at: string;
  };
  added_at: string;
  notes?: string;
  unique_key?: string;
  stock_type?: number;
  strategy_unique_key?: string;
  strategy_name?: string;
}

export interface WatchlistResponse {
  count: number;
  watchlist: WatchlistItem[];
}

export interface AddToWatchlistRequest {
  symbol: string;
  stock_type?: number;
}

// 设置认证token
export const setAuthToken = (token: string) => {
  authToken = token;
  localStorage.setItem('authToken', token);
};

// 获取认证token
export const getAuthToken = (): string | null => {
  if (!authToken) {
    authToken = localStorage.getItem('authToken');
  }
  return authToken;
};

// 清除认证token
export const clearAuthToken = () => {
  authToken = null;
  localStorage.removeItem('authToken');
};

// 通用API请求函数
const apiRequest = async (endpoint: string, options: RequestInit = {}): Promise<any> => {
  const url = `${API_BASE_URL}${endpoint}`;
  const token = getAuthToken();

  const headers: Record<string, string> = {
    'Content-Type': 'application/json',
    ...(options.headers as Record<string, string>),
  };

  if (token) {
    headers.Authorization = `Bearer ${token}`;
  }

  const response = await fetch(url, {
    ...options,
    headers,
  });

  if (!response.ok) {
    const errorData = await response.json().catch(() => ({}));
    throw new Error(errorData.error || `HTTP error! status: ${response.status}`);
  }

  return response.json();
};

// 认证API
export const authAPI = {
  // 用户注册
  register: async (email: string, username: string, password: string): Promise<AuthResponse> => {
    const response = await apiRequest('/auth/register', {
      method: 'POST',
      body: JSON.stringify({ email, username, password }),
    });
    setAuthToken(response.token);
    return response;
  },

  // 用户登录
  login: async (email: string, password: string): Promise<AuthResponse> => {
    const response = await apiRequest('/auth/login', {
      method: 'POST',
      body: JSON.stringify({ email, password }),
    });
    setAuthToken(response.token);
    return response;
  },

  // 获取用户资料
  getProfile: async (): Promise<User> => {
    return apiRequest('/auth/profile');
  },

  // 用户注销
  logout: async (): Promise<void> => {
    await apiRequest('/auth/logout', { method: 'POST' });
    clearAuthToken();
  },
};

// 关注列表API
export const watchlistAPI = {
  getWatchlist: async () => {
    return apiRequest<{ watchlist: WatchlistItem[] }>('/watchlist', { method: 'GET' });
  },
  addToWatchlist: async (data: AddToWatchlistRequest) => {
    return apiRequest<{ message: string; id: number }>('/watchlist', {
      method: 'POST',
      body: JSON.stringify(data),
    });
  },
  removeFromWatchlist: async (id: number) => {
    return apiRequest<{ message: string }>(`/watchlist/${id}`, { method: 'DELETE' });
  },
  bindStrategy: async (symbol: string, strategyUniqueKey: string) => {
    return apiRequest<{ message: string }>('/watchlist/bind', {
      method: 'POST',
      body: JSON.stringify({ symbol, strategy_unique_key: strategyUniqueKey }),
    });
  },
};

export const getPublicPredictions = async (): Promise<PublicPredictionResponse> => {
  return apiRequest<PublicPredictionResponse>('/get-predictions/mtf-best/public', { method: 'GET' });
};

export const getMarketStatus = async () => {
  // Mock data for market status
  return Promise.resolve({
    indices: [
      { name: 'S&P 500', value: 4783.45, change: 1.2 },
      { name: 'NASDAQ', value: 15055.65, change: 1.5 },
      { name: 'DOW', value: 37695.73, change: 0.8 },
      { name: 'VIX', value: 12.45, change: -5.2 }
    ]
  });
};

export const strategyAPI = {
  saveParams: async (params: any): Promise<{ message: string; unique_key: string }> => {
    return apiRequest('/strategy/params', {
      method: 'POST',
      body: JSON.stringify(params),
    });
  },
  getParams: async (uniqueKey: string): Promise<any> => {
    return apiRequest(`/strategy/params/by-unique?unique_key=${uniqueKey}`);
  },
  getUserStrategies: async (): Promise<{ strategies: any[] }> => {
    return apiRequest('/strategy/list');
  },
};

export const quotesAPI = {
  batchLatest: async (symbols: string[]): Promise<{ quotes: Array<{ symbol: string; latest_price?: number; change_percent?: number; trading_date?: string; turnover_rate?: number }> }> => {
    return apiRequest('/quotes/batch-latest', {
      method: 'POST',
      body: JSON.stringify({ symbols }),
    });
  },
};

export const stocksAPI = {
  lookupName: async (symbol: string, stockType: number): Promise<{ symbol: string; name: string }> => {
    const params = new URLSearchParams({ symbol, stock_type: String(stockType) });
    return apiRequest(`/stocks/lookup?${params.toString()}`, { method: 'GET' });
  },
};

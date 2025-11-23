// API服务 - 连接fintrack-api后端
const API_BASE_URL = 'http://localhost:8080/api/v1';

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
}

export interface WatchlistResponse {
  count: number;
  watchlist: WatchlistItem[];
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
  // 获取关注列表
  getWatchlist: async (): Promise<WatchlistResponse> => {
    return apiRequest('/watchlist');
  },

  // 添加股票到关注列表
  addToWatchlist: async (symbol: string, notes?: string): Promise<{ message: string }> => {
    return apiRequest('/watchlist', {
      method: 'POST',
      body: JSON.stringify({ symbol, notes: notes || '' }),
    });
  },

  // 从关注列表删除股票
  removeFromWatchlist: async (id: number): Promise<{ message: string }> => {
    return apiRequest(`/watchlist/${id}`, { method: 'DELETE' });
  },

  // 更新关注列表项目
  updateWatchlistItem: async (id: number, notes: string): Promise<WatchlistItem> => {
    return apiRequest(`/watchlist/${id}`, {
      method: 'PUT',
      body: JSON.stringify({ notes }),
    });
  },
};

// 股票API
export const stockAPI = {
  // 获取所有股票
  getStocks: async (): Promise<any> => {
    return apiRequest('/stocks');
  },

  // 获取特定股票信息
  getStock: async (symbol: string): Promise<any> => {
    return apiRequest(`/stocks/${symbol}`);
  },
};

// 检查用户是否已登录
export const isAuthenticated = (): boolean => {
  return !!getAuthToken();
};
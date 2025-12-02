import React, { createContext, useContext, useState, useEffect, ReactNode } from 'react';

export type Language = 'en' | 'zh';

interface LanguageContextType {
  language: Language;
  setLanguage: (lang: Language) => void;
  t: (key: string) => string;
}

const LanguageContext = createContext<LanguageContextType | undefined>(undefined);

// 翻译文本
const translations = {
  en: {
    // Navigation
    'nav.dashboard': 'Predicted Trends',
    'nav.watchlist': 'Watchlist',
    'nav.portfolio': 'Portfolio',
    'nav.news': 'News',
    'nav.pricing': 'VIP Membership',
    
    // Common
    'common.loading': 'Loading...',
    'common.error': 'Error',
    'common.comingSoon': 'Coming Soon',
    'common.comingSoonDesc': 'This feature is currently under development.',
    'common.settings': 'Settings',
    'common.logout': 'Logout',
    
    // Dashboard
    'dashboard.title': 'Predicted Trends',
    'dashboard.subtitle': 'AI-powered forecasts for your favorite stocks.',
    'dashboard.predictions': 'AI Predictions',
    'dashboard.performance': 'Performance',
    'dashboard.addStock': 'Add Tracking',
    'dashboard.errorTitle': 'An Error Occurred',
    'dashboard.filters.all': 'All',
    'dashboard.filters.highestConfidence': 'Highest Confidence',
    'dashboard.filters.potentialGrowth': 'Potential Growth',
    'dashboard.filters.bullish': 'Bullish',
    'dashboard.filters.bearish': 'Bearish',
    
    // Watchlist
    'watchlist.title': 'My Watchlist',
    'watchlist.subtitle': 'Track your favorite stocks and monitor their performance.',
    'watchlist.searchPlaceholder': 'Search stocks...',
    'watchlist.addStock': 'Add Tracking',
    'watchlist.ticker': 'Ticker / Company',
    'watchlist.lastPrice': 'Last Price',
    'watchlist.todayChange': 'Today\'s Change',
    'watchlist.chart': 'Chart',
    'watchlist.actions': 'Actions',
    'watchlist.emptyTitle': 'Your watchlist is empty',
    'watchlist.emptySubtitle': 'Use the search bar above to find and add your first stock.',
    
    // Pricing
    'pricing.title': 'Unlock Premium Features',
    'pricing.subtitle': 'Enhance your investment strategy with powerful tools and real-time insights designed for serious investors.',
    'pricing.features.realTimeData': 'Real-Time Market Data',
    'pricing.features.realTimeDataDesc': 'Stay ahead of the market with instant data updates, no delays.',
    'pricing.features.advancedCharting': 'Advanced Charting Tools',
    'pricing.features.advancedChartingDesc': 'Utilize professional-grade tools for in-depth technical analysis.',
    'pricing.features.aiInsights': 'AI-Powered Insights',
    'pricing.features.aiInsightsDesc': 'Leverage our AI to analyze your portfolio and uncover new opportunities.',
    'pricing.features.unlimitedWatchlists': 'Unlimited Watchlists',
    'pricing.features.unlimitedWatchlistsDesc': 'Track all the stocks you\'re interested in with no limits.',
    'pricing.features.exclusiveCommunity': 'Exclusive Community',
    'pricing.features.exclusiveCommunityDesc': 'Join a private community of expert traders to share strategies.',
    'pricing.features.adFree': 'Ad-Free Experience',
    'pricing.features.adFreeDesc': 'Focus on your investments with a clean, distraction-free interface.',
    'pricing.comparePlans': 'Compare Our Plans',
    'pricing.feature': 'Feature',
    'pricing.free': 'Free',
    'pricing.vip': 'VIP',
    'pricing.dataRefreshRate': 'Data Refresh Rate',
    'pricing.standard': 'Standard',
    'pricing.realTime': 'Real-time',
    'pricing.numberOfWatchlists': 'Number of Watchlists',
    'pricing.unlimited': 'Unlimited',
    'pricing.advancedAnalytics': 'Advanced Analytics',
    'pricing.aiPortfolioInsights': 'AI Portfolio Insights',
    'pricing.exclusiveCommunityAccess': 'Exclusive Community Access',
    'pricing.prioritySupport': 'Priority Customer Support',
    'pricing.adFreeExperience': 'Ad-Free Experience',
    'pricing.vipMembership': 'VIP Membership',
    'pricing.monthlyPrice': '$19',
    'pricing.perMonth': '/ mo',
    'pricing.billingInfo': 'Billed monthly, cancel anytime.',
    'pricing.allVipFeatures': 'All VIP features included',
    'pricing.priorityCustomerSupport': 'Priority customer support',
    'pricing.earlyAccess': 'Early access to beta features',
    'pricing.upgradeToVip': 'Upgrade to VIP',
    
    // Login
    'login.title': 'Your Portfolio, Perfected.',
    'login.subtitle': 'Track your stocks with AI-powered predictions and unparalleled insight. Make smarter investment decisions today.',
    'login.welcomeBack': 'Welcome Back',
    'login.createAccount': 'Create an Account',
    'login.fullName': 'Full Name',
    'login.fullNamePlaceholder': 'Enter your full name',
    'login.emailAddress': 'Email Address',
    'login.emailPlaceholder': 'Enter your email',
    'login.password': 'Password',
    'login.passwordPlaceholder': 'Enter your password',
    'login.signIn': 'Login',
    'login.register': 'Register',
    'login.forgotPassword': 'Forgot Password?',
    'login.loginTab': 'Login',
    'login.registerTab': 'Register',
    'login.or': 'OR',
    'login.continueWithGoogle': 'Continue with Google',
    'login.loginButton': 'Login',
    'login.registerButton': 'Register',
    
    // Language
    'language.switch': 'Language',
    'language.english': 'English',
    'language.chinese': '中文',
  },
  zh: {
    // Navigation
    'nav.dashboard': '预测趋势',
    'nav.watchlist': '关注列表',
    'nav.portfolio': '投资组合',
    'nav.news': '新闻',
    'nav.pricing': 'VIP会员',
    
    // Common
    'common.loading': '加载中...',
    'common.error': '错误',
    'common.comingSoon': '即将推出',
    'common.comingSoonDesc': '此功能正在开发中。',
    'common.settings': '设置',
    'common.logout': '登出',
    
    // Dashboard
    'dashboard.title': '预测趋势',
    'dashboard.subtitle': '为您喜爱的股票提供AI驱动的预测。',
    'dashboard.predictions': 'AI预测',
    'dashboard.performance': '表现',
    'dashboard.addStock': '添加股票',
    'dashboard.errorTitle': '发生错误',
    'dashboard.filters.all': '全部',
    'dashboard.filters.highestConfidence': '最高置信度',
    'dashboard.filters.potentialGrowth': '潜在增长',
    'dashboard.filters.bullish': '看涨',
    'dashboard.filters.bearish': '看跌',
    
    // Watchlist
    'watchlist.title': '我的关注列表',
    'watchlist.subtitle': '跟踪您喜爱的股票并监控其表现。',
    'watchlist.searchPlaceholder': '搜索股票...',
    'watchlist.addStock': '添加股票',
    'watchlist.ticker': '股票代码 / 公司',
    'watchlist.lastPrice': '最新价格',
    'watchlist.todayChange': '今日变化',
    'watchlist.chart': '图表',
    'watchlist.actions': '操作',
    'watchlist.emptyTitle': '您的关注列表为空',
    'watchlist.emptySubtitle': '使用上方的搜索栏查找并添加您的第一只股票。',
    
    // Pricing
    'pricing.title': '解锁高级功能',
    'pricing.subtitle': '通过为认真投资者设计的强大工具和实时洞察来增强您的投资策略。',
    'pricing.features.realTimeData': '实时市场数据',
    'pricing.features.realTimeDataDesc': '通过即时数据更新保持市场领先，无延迟。',
    'pricing.features.advancedCharting': '高级图表工具',
    'pricing.features.advancedChartingDesc': '利用专业级工具进行深入的技术分析。',
    'pricing.features.aiInsights': 'AI驱动的洞察',
    'pricing.features.aiInsightsDesc': '利用我们的AI分析您的投资组合并发现新机会。',
    'pricing.features.unlimitedWatchlists': '无限关注列表',
    'pricing.features.unlimitedWatchlistsDesc': '无限制地跟踪您感兴趣的所有股票。',
    'pricing.features.exclusiveCommunity': '专属社区',
    'pricing.features.exclusiveCommunityDesc': '加入专家交易者的私人社区，分享策略。',
    'pricing.features.adFree': '无广告体验',
    'pricing.features.adFreeDesc': '专注于您的投资，享受干净、无干扰的界面。',
    'pricing.comparePlans': '比较我们的计划',
    'pricing.feature': '功能',
    'pricing.free': '免费',
    'pricing.vip': 'VIP',
    'pricing.dataRefreshRate': '数据刷新率',
    'pricing.standard': '标准',
    'pricing.realTime': '实时',
    'pricing.numberOfWatchlists': '关注列表数量',
    'pricing.unlimited': '无限制',
    'pricing.advancedAnalytics': '高级分析',
    'pricing.aiPortfolioInsights': 'AI投资组合洞察',
    'pricing.exclusiveCommunityAccess': '专属社区访问',
    'pricing.prioritySupport': '优先客户支持',
    'pricing.adFreeExperience': '无广告体验',
    'pricing.vipMembership': 'VIP会员',
    'pricing.monthlyPrice': '¥128',
    'pricing.perMonth': '/ 月',
    'pricing.billingInfo': '按月计费，随时取消。',
    'pricing.allVipFeatures': '包含所有VIP功能',
    'pricing.priorityCustomerSupport': '优先客户支持',
    'pricing.earlyAccess': '抢先体验测试版功能',
    'pricing.upgradeToVip': '升级到VIP',
    
    // Login
    'login.title': '您的投资组合，完美无缺。',
    'login.subtitle': '通过AI驱动的预测和无与伦比的洞察跟踪您的股票。今天就做出更明智的投资决策。',
    'login.welcomeBack': '欢迎回来',
    'login.createAccount': '创建账户',
    'login.fullName': '姓名',
    'login.fullNamePlaceholder': '请输入您的姓名',
    'login.emailAddress': '邮箱地址',
    'login.emailPlaceholder': '请输入您的邮箱',
    'login.password': '密码',
    'login.passwordPlaceholder': '请输入您的密码',
    'login.signIn': '登录',
    'login.register': '注册',
    'login.forgotPassword': '忘记密码？',
    'login.loginTab': '登录',
    'login.registerTab': '注册',
    'login.or': '或',
    'login.continueWithGoogle': '使用Google继续',
    'login.loginButton': '登录',
    'login.registerButton': '注册',
    
    // Language
    'language.switch': '语言',
    'language.english': 'English',
    'language.chinese': '中文',
  }
};

interface LanguageProviderProps {
  children: ReactNode;
}

export const LanguageProvider: React.FC<LanguageProviderProps> = ({ children }) => {
  const [language, setLanguageState] = useState<Language>('en');

  // 从localStorage加载语言设置
  useEffect(() => {
    const savedLanguage = localStorage.getItem('fintrack-language') as Language;
    if (savedLanguage && (savedLanguage === 'en' || savedLanguage === 'zh')) {
      setLanguageState(savedLanguage);
    }
  }, []);

  // 设置语言并保存到localStorage
  const setLanguage = (lang: Language) => {
    setLanguageState(lang);
    localStorage.setItem('fintrack-language', lang);
  };

  // 翻译函数
  const t = (key: string): string => {
    return translations[language][key] || key;
  };

  const value: LanguageContextType = {
    language,
    setLanguage,
    t,
  };

  return (
    <LanguageContext.Provider value={value}>
      {children}
    </LanguageContext.Provider>
  );
};

// Hook for using language context
export const useLanguage = (): LanguageContextType => {
  const context = useContext(LanguageContext);
  if (context === undefined) {
    throw new Error('useLanguage must be used within a LanguageProvider');
  }
  return context;
};
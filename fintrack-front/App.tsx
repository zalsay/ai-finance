
import React, { useState, useEffect, useCallback } from 'react';
import Login from './components/auth/Login';
import LandingPage from './components/landing/LandingPage';
import Sidebar from './components/layout/Sidebar';
import Dashboard from './components/dashboard/Dashboard';
import Watchlist from './components/watchlist/Watchlist';
import Pricing from './components/pricing/Pricing';
import Portfolio from './components/portfolio/Portfolio';
import { View, StockData } from './types';
import { getStockPredictions } from './services/geminiService';
import { INITIAL_STOCKS, NAVIGATION_ITEMS } from './constants';
import { LanguageProvider, useLanguage } from './contexts/LanguageContext';
import LanguageSwitcher from './components/layout/LanguageSwitcher';
import { authAPI } from './services/apiService';
import ErrorBoundary from './components/ErrorBoundary';

const AppContent: React.FC = () => {
    const { t } = useLanguage();
    const [isAuthenticated, setIsAuthenticated] = useState<boolean>(false);
    const [isCheckingAuth, setIsCheckingAuth] = useState<boolean>(true);
    const [currentView, setCurrentView] = useState<View>('dashboard');
    const [stocks, setStocks] = useState<StockData[]>(INITIAL_STOCKS);
    const [isLoading, setIsLoading] = useState<boolean>(false);
    const [error, setError] = useState<string | null>(null);
    const [isMobileNavOpen, setIsMobileNavOpen] = useState<boolean>(false);

    const [showLogin, setShowLogin] = useState<boolean>(false);
    const [isDemoMode, setIsDemoMode] = useState<boolean>(false);
    const [authRedirecting, setAuthRedirecting] = useState<boolean>(false);

    // 检查用户是否已登录
    useEffect(() => {
        const checkAuth = async () => {
            const token = localStorage.getItem('authToken');  // 修复：使用正确的 key
            if (token) {
                try {
                    // 验证token是否有效
                    await authAPI.getProfile();
                    setIsAuthenticated(true);
                } catch {
                    localStorage.removeItem('authToken');
                    setIsAuthenticated(false);
                }
            }
            setIsCheckingAuth(false);
        };
        checkAuth();
    }, []);

    const handleAuthError = useCallback(() => {
        setAuthRedirecting(true);
        setTimeout(() => {
            localStorage.removeItem('authToken');
            setIsAuthenticated(false);
            setIsDemoMode(false);
            setShowLogin(true);
            setAuthRedirecting(false);
        }, 1500);
    }, []);

    const fetchPredictions = useCallback(async () => {
        setIsLoading(true);
        setError(null);
        try {
            const stockSymbols = INITIAL_STOCKS.map(s => s.symbol);
            const predictions = await getStockPredictions(stockSymbols);
            setStocks(prevStocks => prevStocks.map(stock => ({
                ...stock,
                prediction: predictions[stock.symbol] || stock.prediction,
            })));
        } catch (err: any) {
            // 如果是授权错误，自动跳转登录
            if (err.message && (
                err.message.includes('Authorization header required') || 
                err.message.includes('401') ||
                err.message.includes('Unauthorized')
            )) {
                handleAuthError();
            } else {
                setError(err.message);
                console.error(err);
            }
        } finally {
            setIsLoading(false);
        }
    }, [handleAuthError]);

    useEffect(() => {
        if (isAuthenticated || isDemoMode) {
            fetchPredictions();
        }
    }, [isAuthenticated, isDemoMode, fetchPredictions]);

    const handleLogin = () => {
        setIsAuthenticated(true);
    };

    const handleLogout = async () => {
        try {
            await authAPI.logout();
        } catch (error) {
            console.error('Logout error:', error);
        } finally {
            localStorage.removeItem('authToken');  // 修复：使用正确的 key
            setIsAuthenticated(false);
            setCurrentView('dashboard');
            setShowLogin(false); // Reset to landing page on logout
        }
    };

    const renderView = () => {
        switch (currentView) {
            case 'dashboard':
                return <Dashboard 
                    stocks={stocks} 
                    isLoading={isLoading} 
                    error={error} 
                    onAuthError={handleAuthError}
                />;
            case 'watchlist':
                return <Watchlist 
                    initialStocks={INITIAL_STOCKS} 
                    onAuthError={handleAuthError}
                />;
            case 'pricing':
                return <Pricing />;
            case 'portfolio':
                return <Portfolio />;
            default:
                return <div className="text-center p-8 bg-card-dark rounded-lg">
                    <h2 className="text-2xl font-bold">{t('common.comingSoon')}</h2>
                    <p className="text-white/60 mt-2">{t('common.comingSoonDesc')}</p>
                </div>;
        }
    };

    // 显示加载画面，等待token验证完成
    if (isCheckingAuth) {
        return (
            <div className="flex items-center justify-center min-h-screen bg-background-dark">
                <div className="text-center">
                    <div className="w-16 h-16 border-4 border-primary border-t-transparent rounded-full animate-spin mx-auto mb-4"></div>
                    <p className="text-white/60">正在验证登录状态...</p>
                </div>
            </div>
        );
    }

    if (!isAuthenticated && !isDemoMode) {
        if (showLogin) {
            return <Login onLogin={handleLogin} onBack={() => setShowLogin(false)} />;
        }
        return <LandingPage onLogin={() => setShowLogin(true)} onRegister={() => setShowLogin(true)} onDemo={() => setIsDemoMode(true)} />;
    }

    return (
        <div className="flex min-h-screen">
            {/* Auth Redirect Overlay */}
            {authRedirecting && (
                <div className="fixed inset-0 z-[100] flex items-center justify-center bg-black/60 backdrop-blur-sm">
                    <div className="bg-card-dark border border-white/10 rounded-xl p-6 shadow-2xl max-w-sm w-full mx-4 text-center transform transition-all">
                        <div className="w-12 h-12 rounded-full bg-primary/20 flex items-center justify-center mx-auto mb-4">
                            <span className="material-symbols-outlined text-primary text-2xl">lock</span>
                        </div>
                        <h3 className="text-xl font-bold text-white mb-2">{t('auth.sessionExpired')}</h3>
                        <p className="text-white/60 mb-6">{t('auth.redirectingLogin')}</p>
                        <div className="w-full bg-white/10 rounded-full h-1 overflow-hidden">
                            <div className="bg-primary h-full rounded-full w-full animate-[pulse_1.5s_ease-in-out_infinite]"></div>
                        </div>
                    </div>
                </div>
            )}

            <Sidebar currentView={currentView} setCurrentView={setCurrentView} onLogout={handleLogout} />

            {/* Mobile Navigation */}
            <div className="lg:hidden fixed bottom-0 left-0 right-0 bg-[#11221a] border-t border-white/10 z-50 safe-area-inset-bottom">
                <div className="flex justify-around items-center h-16">
                    {NAVIGATION_ITEMS.slice(0, 4).map(item => (
                        <button
                            key={item.id}
                            onClick={() => setCurrentView(item.id)}
                            className={`flex flex-col items-center justify-center py-1 px-2 w-full h-full transition-colors ${currentView === item.id ? 'text-primary' : 'text-white/60 hover:text-white'
                                }`}
                        >
                            <span className="material-symbols-outlined text-lg" style={{ fontVariationSettings: currentView === item.id ? "'FILL' 1" : "" }}>
                                {item.icon}
                            </span>
                            <span className="text-[9px] mt-0.5 truncate leading-tight">{t(`nav.${item.id}`)}</span>
                        </button>
                    ))}
                    {/* Language Switcher for Mobile */}
                    <div className="flex flex-col items-center justify-center py-1 px-2 w-full h-full">
                        <div className="scale-[0.65] origin-center">
                            <LanguageSwitcher />
                        </div>
                    </div>
                </div>
            </div>

            <main className="flex-1 p-3 sm:p-6 lg:p-8 pb-20 sm:pb-24 lg:pb-8 min-h-screen lg:min-h-0">
                <div className="max-w-full overflow-x-auto">
                    {renderView()}
                </div>
            </main>
        </div>
    );
};

const App: React.FC = () => {
    return (
        <LanguageProvider>
            <ErrorBoundary>
                <AppContent />
            </ErrorBoundary>
        </LanguageProvider>
    );
};

export default App;

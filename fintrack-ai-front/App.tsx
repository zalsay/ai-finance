
import React, { useState, useEffect, useCallback } from 'react';
import Login from './components/auth/Login';
import Sidebar from './components/layout/Sidebar';
import Dashboard from './components/dashboard/Dashboard';
import Watchlist from './components/watchlist/Watchlist';
import Pricing from './components/pricing/Pricing';
import { View, StockData } from './types';
import { getStockPredictions } from './services/geminiService';
import { INITIAL_STOCKS, NAVIGATION_ITEMS } from './constants';
import { LanguageProvider, useLanguage } from './contexts/LanguageContext';
import LanguageSwitcher from './components/layout/LanguageSwitcher';
import { authAPI } from './services/apiService';

const AppContent: React.FC = () => {
    const { t } = useLanguage();
    const [isAuthenticated, setIsAuthenticated] = useState<boolean>(false);
    const [currentView, setCurrentView] = useState<View>('dashboard');
    const [stocks, setStocks] = useState<StockData[]>(INITIAL_STOCKS);
    const [isLoading, setIsLoading] = useState<boolean>(false);
    const [error, setError] = useState<string | null>(null);
    const [isMobileNavOpen, setIsMobileNavOpen] = useState<boolean>(false);

    // 检查用户是否已登录
    useEffect(() => {
        const token = localStorage.getItem('token');
        if (token) {
            // 验证token是否有效
            authAPI.getProfile()
                .then(() => setIsAuthenticated(true))
                .catch(() => {
                    localStorage.removeItem('token');
                    setIsAuthenticated(false);
                });
        }
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
            setError(err.message);
            console.error(err);
        } finally {
            setIsLoading(false);
        }
    }, []);

    useEffect(() => {
        if (isAuthenticated) {
            fetchPredictions();
        }
    }, [isAuthenticated, fetchPredictions]);

    const handleLogin = () => {
        setIsAuthenticated(true);
    };
    
    const handleLogout = async () => {
        try {
            await authAPI.logout();
        } catch (error) {
            console.error('Logout error:', error);
        } finally {
            localStorage.removeItem('token');
            setIsAuthenticated(false);
            setCurrentView('dashboard');
        }
    };

    const renderView = () => {
        switch (currentView) {
            case 'dashboard':
                return <Dashboard stocks={stocks} isLoading={isLoading} error={error} />;
            case 'watchlist':
                return <Watchlist initialStocks={INITIAL_STOCKS} />;
            case 'pricing':
                return <Pricing />;
            default:
                return <div className="text-center p-8 bg-card-dark rounded-lg">
                    <h2 className="text-2xl font-bold">{t('common.comingSoon')}</h2>
                    <p className="text-white/60 mt-2">{t('common.comingSoonDesc')}</p>
                </div>;
        }
    };
    
    if (!isAuthenticated) {
        return <Login onLogin={handleLogin} />;
    }

    return (
        <div className="flex min-h-screen">
            <Sidebar currentView={currentView} setCurrentView={setCurrentView} onLogout={handleLogout} />
            
            {/* Mobile Navigation */}
             <div className="lg:hidden fixed bottom-0 left-0 right-0 bg-[#11221a] border-t border-white/10 z-50 safe-area-inset-bottom">
                <div className="flex justify-around items-center h-16">
                    {NAVIGATION_ITEMS.slice(0, 4).map(item => (
                         <button
                            key={item.id}
                            onClick={() => setCurrentView(item.id)}
                            className={`flex flex-col items-center justify-center py-1 px-2 w-full h-full transition-colors ${
                                currentView === item.id ? 'text-primary' : 'text-white/60 hover:text-white'
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
            <AppContent />
        </LanguageProvider>
    );
};

export default App;

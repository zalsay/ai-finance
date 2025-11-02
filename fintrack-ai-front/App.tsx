
import React, { useState, useEffect, useCallback } from 'react';
import Login from './components/auth/Login';
import Sidebar from './components/layout/Sidebar';
import Dashboard from './components/dashboard/Dashboard';
import Watchlist from './components/watchlist/Watchlist';
import Pricing from './components/pricing/Pricing';
import { View, StockData } from './types';
import { getStockPredictions } from './services/geminiService';
import { INITIAL_STOCKS, NAVIGATION_ITEMS } from './constants';

const App: React.FC = () => {
    const [isAuthenticated, setIsAuthenticated] = useState<boolean>(false);
    const [currentView, setCurrentView] = useState<View>('dashboard');
    const [stocks, setStocks] = useState<StockData[]>(INITIAL_STOCKS);
    const [isLoading, setIsLoading] = useState<boolean>(false);
    const [error, setError] = useState<string | null>(null);
    const [isMobileNavOpen, setIsMobileNavOpen] = useState<boolean>(false);

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
    
    const handleLogout = () => {
        setIsAuthenticated(false);
        setCurrentView('dashboard');
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
                    <h2 className="text-2xl font-bold">Coming Soon</h2>
                    <p className="text-white/60 mt-2">This feature is currently under development.</p>
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
             <div className="lg:hidden fixed bottom-0 left-0 right-0 bg-[#11221a] border-t border-white/10 z-50">
                <div className="flex justify-around">
                    {NAVIGATION_ITEMS.slice(0, 5).map(item => (
                         <button
                            key={item.id}
                            onClick={() => setCurrentView(item.id)}
                            className={`flex flex-col items-center justify-center p-2 w-full transition-colors ${
                                currentView === item.id ? 'text-primary' : 'text-white/60 hover:text-white'
                            }`}
                         >
                            <span className="material-symbols-outlined" style={{ fontVariationSettings: currentView === item.id ? "'FILL' 1" : "" }}>
                                {item.icon}
                            </span>
                             <span className="text-[10px] truncate">{item.label}</span>
                         </button>
                    ))}
                </div>
             </div>

            <main className="flex-1 p-4 sm:p-8 pb-20 lg:pb-8">
                {renderView()}
            </main>
        </div>
    );
};

export default App;

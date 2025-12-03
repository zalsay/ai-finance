
import React, { useState, useEffect } from 'react';
import { StockData, MarketStatus } from '../../types';
import { getMarketStatus, getPublicPredictions, watchlistAPI } from '../../services/apiService';
import { useLanguage } from '../../contexts/LanguageContext';
import StockChart from './StockChart';

const Dashboard: React.FC = () => {
    const { t, language } = useLanguage();
    const [marketStatus, setMarketStatus] = useState<MarketStatus | null>(null);
    const [publicStocks, setPublicStocks] = useState<StockData[]>([]);
    const [isLoading, setIsLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);
    const [addingToWatchlist, setAddingToWatchlist] = useState<string | null>(null);

    useEffect(() => {
        const fetchData = async () => {
            try {
                const [statusRes, publicRes] = await Promise.all([
                    getMarketStatus(),
                    getPublicPredictions()
                ]);
                setMarketStatus(statusRes);
                
                if (publicRes && publicRes.items) {
                    const mapped = publicRes.items.map(item => ({
                        symbol: item.best.symbol,
                        companyName: item.best.short_name || item.best.symbol,
                        currentPrice: 0, // Public endpoint doesn't provide price
                        changePercent: 0,
                        uniqueKey: item.best.unique_key
                    }));
                    setPublicStocks(mapped);
                }
            } catch (err) {
                console.error('Failed to fetch dashboard data:', err);
                setError('Failed to load dashboard data');
            } finally {
                setIsLoading(false);
            }
        };

        fetchData();
    }, []);

    const handleAddToWatchlist = async (symbol: string) => {
        setAddingToWatchlist(symbol);
        try {
            await watchlistAPI.addToWatchlist({ symbol });
            // Optional: Show success toast
        } catch (error) {
            console.error('Failed to add to watchlist:', error);
            // Optional: Show error toast
        } finally {
            setAddingToWatchlist(null);
        }
    };

    if (isLoading) {
        return (
            <div className="flex flex-col gap-6">
                <header className="flex flex-wrap justify-between gap-4 items-center">
                    <div className="flex flex-col gap-1">
                        <h1 className="text-white text-4xl font-black leading-tight tracking-[-0.033em]">
                            {t('dashboard.title')}
                        </h1>
                        <p className="text-white/60 text-base font-normal leading-normal">
                            {t('dashboard.subtitle')}
                        </p>
                    </div>
                    <div className="flex gap-2">
                        <button className="flex items-center justify-center p-2 rounded-lg text-white/80 bg-white/5 hover:bg-white/10 transition-colors">
                            <span className="material-symbols-outlined">notifications</span>
                        </button>
                        <button className="flex items-center justify-center p-2 rounded-lg text-white/80 bg-white/5 hover:bg-white/10 transition-colors">
                            <span className="material-symbols-outlined">settings</span>
                        </button>
                    </div>
                </header>
                <div className="flex items-center justify-center h-64">
                    <span className="material-symbols-outlined animate-spin text-4xl text-primary">progress_activity</span>
                </div>
            </div>
        );
    }

    return (
        <div className="flex flex-col gap-6">
            <header className="flex flex-wrap justify-between gap-4 items-center">
                <div className="flex flex-col gap-1">
                    <h1 className="text-white text-4xl font-black leading-tight tracking-[-0.033em]">
                        {t('dashboard.title')}
                    </h1>
                    <p className="text-white/60 text-base font-normal leading-normal">
                        {t('dashboard.subtitle')}
                    </p>
                </div>
                <div className="flex gap-2">
                    <button className="flex items-center justify-center p-2 rounded-lg text-white/80 bg-white/5 hover:bg-white/10 transition-colors">
                        <span className="material-symbols-outlined">notifications</span>
                    </button>
                    <button className="flex items-center justify-center p-2 rounded-lg text-white/80 bg-white/5 hover:bg-white/10 transition-colors">
                        <span className="material-symbols-outlined">settings</span>
                    </button>
                </div>
            </header>

            {/* Market Status Cards */}
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
                {marketStatus?.indices.map((index) => (
                    <div key={index.name} className="bg-[#1C1C1C] rounded-xl p-4 border border-white/10">
                        <div className="flex justify-between items-start mb-2">
                            <span className="text-white/60 text-sm">{index.name}</span>
                            <span className={`text-sm font-medium ${index.change >= 0 ? 'text-green-400' : 'text-red-400'}`}>
                                {index.change >= 0 ? '+' : ''}{index.change}%
                            </span>
                        </div>
                        <div className="text-white text-xl font-bold">{index.value.toLocaleString()}</div>
                    </div>
                ))}
            </div>

            {/* Public Predictions / Market Overview */}
            <section>
                <h2 className="text-white text-xl font-bold mb-4">
                    {language === 'zh' ? '市场概览' : 'Market Overview'}
                </h2>
                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                    {publicStocks.map((stock) => (
                        <div key={stock.symbol} className="bg-[#1C1C1C] rounded-xl p-4 border border-white/10">
                            <div className="flex justify-between items-start mb-4">
                                <div>
                                    <div className="text-white font-bold text-lg">{stock.symbol}</div>
                                    <div className="text-white/60 text-sm">{stock.companyName}</div>
                                </div>
                                <button 
                                    onClick={() => handleAddToWatchlist(stock.symbol)}
                                    disabled={addingToWatchlist === stock.symbol}
                                    className="flex items-center justify-center w-8 h-8 rounded-full bg-white/10 hover:bg-white/20 transition-colors disabled:opacity-50"
                                    title={language === 'zh' ? "添加到关注列表" : "Add to Watchlist"}
                                >
                                    {addingToWatchlist === stock.symbol ? (
                                        <span className="material-symbols-outlined text-sm animate-spin">progress_activity</span>
                                    ) : (
                                        <span className="material-symbols-outlined text-sm">add</span>
                                    )}
                                </button>
                            </div>
                            <div className="h-32 bg-white/5 rounded-lg flex items-center justify-center mb-2">
                                <span className="text-white/20 text-sm">Chart Preview</span>
                            </div>
                            <div className="flex justify-between items-center text-sm">
                                <span className="text-white/40">
                                    {language === 'zh' ? '预测置信度' : 'Prediction Confidence'}
                                </span>
                                <span className="text-green-400 font-medium">High</span>
                            </div>
                        </div>
                    ))}
                </div>
            </section>
        </div>
    );
};

export default Dashboard;

import React, { useState, useEffect } from 'react';
import { StockData } from '../../types';
import StrategyCard from '../dashboard/StrategyCard';
import { useLanguage } from '../../contexts/LanguageContext';
import { watchlistAPI } from '../../services/apiService';

interface PortfolioProps {
    onAuthError?: () => void;
}

const Portfolio: React.FC<PortfolioProps> = ({ onAuthError }) => {
    const { t, language } = useLanguage();
    const [portfolioStocks, setPortfolioStocks] = useState<StockData[]>([]);
    const [isFetching, setIsFetching] = useState(true);
    const [fetchError, setFetchError] = useState<string | null>(null);

    useEffect(() => {
        const fetchWatchlist = async () => {
            setIsFetching(true);
            setFetchError(null);
            try {
                // Use watchlistAPI to get personal watchlist
                const res = await watchlistAPI.getWatchlist();
                if (res && res.watchlist) {
                    const mapped = res.watchlist.map(item => {
                        if (!item.unique_key) return null;
                        return {
                            symbol: item.stock.symbol,
                            uniqueKey: item.unique_key, 
                            companyName: item.stock.company_name || item.stock.symbol,
                            currentPrice: item.current_price?.price || 0, 
                            changePercent: item.current_price?.change_percent || 0,
                        } as StockData;
                    }).filter((item): item is StockData => item !== null);
                    setPortfolioStocks(mapped);
                }
            } catch (e: any) {
                console.error("Fetch error", e);
                if (onAuthError && e.message && (
                    e.message.includes('Authorization header required') || 
                    e.message.includes('401') ||
                    e.message.includes('Unauthorized')
                )) {
                    onAuthError();
                } else {
                    setFetchError(e.message || "Failed to load watchlist strategies");
                }
            } finally {
                setIsFetching(false);
            }
        };
        fetchWatchlist();
    }, [onAuthError]);

    return (
        <div className="flex flex-col gap-6">
            <header className="flex flex-wrap justify-between gap-4 items-center">
                <div className="flex flex-col gap-1">
                    <h1 className="text-white text-4xl font-black leading-tight tracking-[-0.033em]">
                        {language === 'zh' ? '投资组合策略' : 'Portfolio Strategies'}
                    </h1>
                    <p className="text-white/60 text-base font-normal leading-normal">
                        {language === 'zh' ? '管理您关注列表中的自动化投资策略' : 'Manage automated investment strategies for your watchlist'}
                    </p>
                </div>
            </header>

            {/* Strategy Section */}
            {isFetching ? (
                 <div className="flex items-center justify-center h-64">
                    <span className="material-symbols-outlined animate-spin text-4xl text-primary">progress_activity</span>
                 </div>
            ) : fetchError ? (
                <div 
                    onClick={onAuthError}
                    className={`p-4 rounded-lg bg-red-500/10 border border-red-500/20 text-red-400 ${onAuthError ? 'cursor-pointer hover:bg-red-500/20 transition-colors' : ''}`}
                >
                    {fetchError}
                </div>
            ) : portfolioStocks.length > 0 ? (
                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                    {portfolioStocks.map((stock: any) => (
                            stock.uniqueKey ? (
                            <StrategyCard 
                                key={`strat-${stock.uniqueKey}`} 
                                uniqueKey={stock.uniqueKey} 
                                symbol={stock.symbol}
                            />
                            ) : null
                    ))}
                </div>
            ) : (
                <div className="text-center py-12 bg-white/5 rounded-xl border border-white/10">
                    <span className="material-symbols-outlined text-4xl text-white/20 mb-4">playlist_add</span>
                    <p className="text-white/40 mb-4">
                        {language === 'zh' ? '您的关注列表为空或没有可用的策略。' : 'Your watchlist is empty or has no available strategies.'}
                    </p>
                    <p className="text-white/60 text-sm">
                        {language === 'zh' ? '请先添加股票到关注列表。' : 'Please add stocks to your watchlist first.'}
                    </p>
                </div>
            )}
        </div>
    );
};

export default Portfolio;

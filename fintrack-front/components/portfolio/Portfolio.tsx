import React, { useState, useEffect, useCallback } from 'react';
import { StockData } from '../../types';
import StrategyCard from '../dashboard/StrategyCard';
import CreateStrategyModal from '../dashboard/CreateStrategyModal';
import BindStrategyModal from './BindStrategyModal';
import { useLanguage } from '../../contexts/LanguageContext';
import { watchlistAPI, strategyAPI } from '../../services/apiService';

interface PortfolioProps {
    onAuthError?: () => void;
}

const Portfolio: React.FC<PortfolioProps> = ({ onAuthError }) => {
    const { t, language } = useLanguage();
    const [portfolioStocks, setPortfolioStocks] = useState<StockData[]>([]);
    const [watchlistItems, setWatchlistItems] = useState<any[]>([]);
    const [userStrategies, setUserStrategies] = useState<any[]>([]);
    const [isFetching, setIsFetching] = useState(true);
    const [fetchError, setFetchError] = useState<string | null>(null);
    const [isModalOpen, setIsModalOpen] = useState(false);
    const [refreshKey, setRefreshKey] = useState(0);
    const [bindingLoading, setBindingLoading] = useState<string | null>(null); // symbol being bound
    const [bindModalData, setBindModalData] = useState<{symbol: string, currentKey: string | null} | null>(null);

    const fetchWatchlist = useCallback(async () => {
        setIsFetching(true);
        setFetchError(null);
        try {
            // Parallel fetch
            const [watchlistRes, strategiesRes] = await Promise.all([
                watchlistAPI.getWatchlist(),
                strategyAPI.getUserStrategies()
            ]);

            if (strategiesRes && strategiesRes.strategies) {
                setUserStrategies(strategiesRes.strategies);
            }

            if (watchlistRes && watchlistRes.watchlist) {
                setWatchlistItems(watchlistRes.watchlist);
                
                const mapped = watchlistRes.watchlist.map(item => {
                    if (!item.unique_key) return null;
                    return {
                        symbol: item.stock.symbol,
                        uniqueKey: item.strategy_unique_key || item.unique_key, 
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
    }, [onAuthError]);

    useEffect(() => {
        fetchWatchlist();
    }, [fetchWatchlist, refreshKey]);

    const handleSuccess = () => {
        setRefreshKey(prev => prev + 1);
    };

    const handleBind = async (symbol: string, strategyKey: string) => {
        if (!symbol || !strategyKey) return;
        setBindingLoading(symbol);
        try {
            await watchlistAPI.bindStrategy(symbol, strategyKey);
            await fetchWatchlist();
            handleSuccess();
        } catch (e: any) {
            console.error(e);
            // Optional: Show toast error
        } finally {
            setBindingLoading(null);
        }
    };

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
            ) : (
                <div className="space-y-8">
                    {/* Official Strategies */}
                    {userStrategies.some(s => s.is_public === 1) && (
                        <div className="space-y-3">
                            <h3 className="text-white/60 text-sm font-medium uppercase tracking-wider">{language === 'zh' ? '官方推荐' : 'Official Recommended'}</h3>
                            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                                {userStrategies
                                    .filter(s => s.is_public === 1)
                                    .map((strategy) => (
                                        <StrategyCard 
                                            key={`strat-${strategy.unique_key}`} 
                                            uniqueKey={strategy.unique_key} 
                                            symbol={strategy.name || 'Strategy'}
                                        />
                                    ))
                                }
                            </div>
                        </div>
                    )}

                    {/* Personal Strategies */}
                    <div className="space-y-3">
                        <h3 className="text-white/60 text-sm font-medium uppercase tracking-wider">{language === 'zh' ? '个人策略' : 'My Strategies'}</h3>
                        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                            {userStrategies
                                .filter(s => s.is_public !== 1)
                                .map((strategy) => (
                                    <StrategyCard 
                                        key={`strat-${strategy.unique_key}`} 
                                        uniqueKey={strategy.unique_key} 
                                        symbol={strategy.name || 'Strategy'}
                                    />
                                ))
                            }
                            
                            <button
                                onClick={() => setIsModalOpen(true)}
                                className="rounded-xl bg-white/5 border border-dashed border-white/20 hover:border-primary/50 hover:bg-white/10 transition-all p-5 flex flex-col items-center justify-center h-full min-h-[200px] group"
                            >
                                <div className="w-12 h-12 rounded-full bg-primary/10 text-primary flex items-center justify-center mb-3 group-hover:scale-110 transition-transform">
                                    <span className="material-symbols-outlined text-2xl">add</span>
                                </div>
                                <span className="text-white font-bold text-lg">{language === 'zh' ? '添加策略' : 'Add Strategy'}</span>
                                <p className="text-white/40 text-xs mt-1">{language === 'zh' ? '为新股票配置策略' : 'Configure strategy for new stock'}</p>
                            </button>
                        </div>
                    </div>
                </div>
            )}
            
            {/* Watchlist Binding Section */}
            <div className="bg-[#1E1E1E] rounded-xl border border-white/10 overflow-hidden">
                <div className="p-6 border-b border-white/10">
                    <h2 className="text-xl font-bold text-white">
                        {language === 'zh' ? '策略绑定' : 'Strategy Bindings'}
                    </h2>
                    <p className="text-white/60 text-sm mt-1">
                        {language === 'zh' ? '将策略应用到关注列表中的股票' : 'Apply strategies to stocks in your watchlist'}
                    </p>
                </div>
                
                <div className="overflow-x-auto">
                    <table className="w-full text-left text-sm text-white/60">
                        <thead className="bg-white/5 text-xs uppercase font-semibold text-white/40">
                            <tr>
                                <th className="px-6 py-4">{language === 'zh' ? '股票' : 'Stock'}</th>
                                <th className="px-6 py-4">{language === 'zh' ? '当前策略' : 'Current Strategy'}</th>
                                <th className="px-6 py-4">{language === 'zh' ? '操作' : 'Action'}</th>
                            </tr>
                        </thead>
                        <tbody className="divide-y divide-white/5">
                            {watchlistItems.map((item) => {
                                const currentStrategy = userStrategies.find(s => s.unique_key === item.strategy_unique_key);
                                const isBinding = bindingLoading === item.stock.symbol;
                                
                                return (
                                    <tr key={item.id} className="hover:bg-white/5 transition-colors">
                                        <td className="px-6 py-4">
                                            <div className="flex flex-col">
                                                <span className="text-white font-medium font-mono">{item.stock.symbol}</span>
                                                <span className="text-xs">{item.stock.company_name}</span>
                                            </div>
                                        </td>
                                        <td className="px-6 py-4">
                                            {currentStrategy ? (
                                                <div className="flex items-center gap-2">
                                                    <span className="text-primary font-medium">{currentStrategy.name || 'Unnamed Strategy'}</span>
                                                    {currentStrategy.is_public === 1 ? (
                                                        <span className="text-[10px] px-1.5 py-0.5 rounded bg-blue-500/20 text-blue-400 font-medium whitespace-nowrap">
                                                            {language === 'zh' ? '官方' : 'Official'}
                                                        </span>
                                                    ) : (
                                                        <span className="text-[10px] px-1.5 py-0.5 rounded bg-purple-500/20 text-purple-400 font-medium whitespace-nowrap">
                                                            {language === 'zh' ? '个人' : 'Personal'}
                                                        </span>
                                                    )}
                                                    <span className="text-[10px] px-1.5 py-0.5 rounded bg-primary/10 text-primary/80 font-mono">
                                                        {currentStrategy.buy_threshold_pct}% | {currentStrategy.sell_threshold_pct}%
                                                    </span>
                                                </div>
                                            ) : (
                                                <span className="text-white/20 italic">{language === 'zh' ? '未绑定' : 'Unbound'}</span>
                                            )}
                                        </td>
                                        <td className="px-6 py-4">
                                            {item.unique_key ? (
                                                <div className="flex items-center gap-2">
                                                    <button
                                                        onClick={() => setBindModalData({
                                                            symbol: item.stock.symbol,
                                                            currentKey: item.strategy_unique_key || null
                                                        })}
                                                        disabled={isBinding}
                                                        className="px-3 py-1.5 rounded-md bg-white/5 border border-white/10 text-white text-xs font-medium hover:bg-white/10 hover:border-white/20 transition-all min-w-[100px] text-center"
                                                    >
                                                        {item.strategy_unique_key 
                                                            ? (language === 'zh' ? '换绑' : 'Change')
                                                            : (language === 'zh' ? '绑定' : 'Bind')}
                                                    </button>
                                                    {isBinding && <span className="material-symbols-outlined animate-spin text-primary text-sm">progress_activity</span>}
                                                </div>
                                            ) : (
                                                <span className="text-white/20 text-xs cursor-help" title={language === 'zh' ? '该股票暂无AI预测模型支持，无法绑定策略' : 'No AI model available for this stock'}>
                                                    {language === 'zh' ? '不可用' : 'Unavailable'}
                                                </span>
                                            )}
                                        </td>
                                    </tr>
                                );
                            })}
                            {watchlistItems.length === 0 && (
                                <tr>
                                    <td colSpan={3} className="px-6 py-8 text-center text-white/40">
                                        {language === 'zh' ? '关注列表为空' : 'Watchlist is empty'}
                                    </td>
                                </tr>
                            )}
                        </tbody>
                    </table>
                </div>
            </div>

            <BindStrategyModal
                isOpen={!!bindModalData}
                onClose={() => setBindModalData(null)}
                symbol={bindModalData?.symbol || ''}
                strategies={userStrategies}
                currentStrategyKey={bindModalData?.currentKey || undefined}
                onBind={handleBind}
            />

            <CreateStrategyModal 
                isOpen={isModalOpen}
                onClose={() => setIsModalOpen(false)}
                onSuccess={handleSuccess}
            />
        </div>
    );
};

export default Portfolio;

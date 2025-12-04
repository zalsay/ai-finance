
import React, { useState, useEffect } from 'react';
import { StockData } from '../../types';
import { useLanguage } from '../../contexts/LanguageContext';
import { getChangeColors } from '../../utils/colorUtils';
import { watchlistAPI, WatchlistItem, quotesAPI, getPublicPredictions } from '../../services/apiService';
import AddStockModal from '../dashboard/AddStockModal';
import ConfirmModal from '../common/ConfirmModal';
import PredictionChart from '../common/PredictionChart';

interface WatchlistProps {
    initialStocks: StockData[];
    onAuthError?: () => void;
}

const Sparkline: React.FC<{ change: number }> = ({ change }) => {
    const isPositive = change >= 0;
    const src = isPositive
        ? "https://lh3.googleusercontent.com/aida-public/AB6AXuD4YDeRvouHCRlEkQ0zH8WxZ_g_h8laGqNAh7bK7TsNWt54rhvgTaYYRhMDeHoVKQL5OeRVcrCXeW6JxeIfqNURF01it8sBR_zK2eomsM8SVaTE5cP2ydv8MCzYcAYy5QocrGnvYOjrLUOVOrRj5NlXfk10CiqpwapQXXh7L71O1V4Px83vxAxY3wRGoiEA5-Da7GaAim27zKhzR20yI-Ml_JBMrwEqUljK9-HpZAyzJk7vgRXbMn4IxHNm8bm1GBhtxCY1zuLA8w"
        : "https://lh3.googleusercontent.com/aida-public/AB6AXuC5ysC61emay1Sky-PhL9F5U9VC5-YfNi2tYQPpVNujonl5kI-7qndFO4McJDnZK0GK2jsOhGkj_8ouOnRjCu5XH7ugJ1ZLQQIGd0iR6dfUPTOWhc7Q8l5nfv0E5v60o4nWgn12UQQYrs5sBd_D8Aba3BdJAjxGaA2c7xWwsZOv6zYdYip3ZMaM0s4vStW2wBJ2-uyB3dzyr615XjIvO4C_rHcvs70LdHIeahK7q3j0ajRQBWcWnvGsfiL6d_uGRNiuNOXwfccRxQ";
    return <img className="h-8 w-full object-contain" alt={isPositive ? "Upward trend sparkline" : "Downward trend sparkline"} src={src} />;
};

const Watchlist: React.FC<WatchlistProps> = ({ initialStocks, onAuthError }) => {
    const { t, language } = useLanguage();
    const [watchlistItems, setWatchlistItems] = useState<WatchlistItem[]>([]);
    const [activeTab, setActiveTab] = useState<1 | 2>(1);
    const [searchTerm, setSearchTerm] = useState('');
    const [isModalOpen, setIsModalOpen] = useState(false);
    const [deleteModalOpen, setDeleteModalOpen] = useState(false);
    const [stockToDelete, setStockToDelete] = useState<{ id: number; symbol: string } | null>(null);
    const [selectedStock, setSelectedStock] = useState<StockData | null>(null);
    const [chartOpen, setChartOpen] = useState(false);
    const [isLoading, setIsLoading] = useState(false);
    const [isChartLoading, setIsChartLoading] = useState(false);
    const [error, setError] = useState<string | null>(null);
    const [latestQuotes, setLatestQuotes] = useState<Record<string, { latest_price?: number; change_percent?: number; trading_date?: string; turnover_rate?: number }>>({});

    useEffect(() => {
        loadWatchlist();
    }, []);

    const loadWatchlist = async () => {
        try {
            setIsLoading(true);
            const response = await watchlistAPI.getWatchlist();
            setWatchlistItems(response.watchlist || []);
            const symbols = (response.watchlist || []).map((it: WatchlistItem) => it.stock?.symbol).filter(Boolean) as string[];
            if (symbols.length > 0) {
                try {
                    const res = await quotesAPI.batchLatest(symbols);
                    const map: Record<string, { latest_price?: number; change_percent?: number; trading_date?: string; turnover_rate?: number }> = {};
                    for (const q of res.quotes || []) {
                        map[q.symbol] = { latest_price: q.latest_price, change_percent: q.change_percent, trading_date: q.trading_date, turnover_rate: q.turnover_rate };
                    }
                    setLatestQuotes(map);
                } catch (e) { }
            } else {
                setLatestQuotes({});
            }
        } catch (err: any) {
            if (onAuthError && err.message && (
                err.message.includes('Authorization header required') ||
                err.message.includes('401') ||
                err.message.includes('Unauthorized')
            )) {
                onAuthError();
            } else {
                setError(err.message);
            }
        } finally {
            setIsLoading(false);
        }
    };

    const handleAddStock = async (symbol: string, type: 1 | 2) => {
        try {
            const symLower = symbol.toLowerCase();
            const exists = watchlistItems.some(it => (it.stock?.symbol || '').toLowerCase() === symLower);
            if (exists) {
                throw new Error('duplicate symbol');
            }

            await watchlistAPI.addToWatchlist({ symbol: symbol.toUpperCase(), stock_type: type });
            await loadWatchlist();
        } catch (err: any) {
            if (onAuthError && err.message && (
                err.message.includes('Authorization header required') ||
                err.message.includes('401') ||
                err.message.includes('Unauthorized')
            )) {
                onAuthError();
                return;
            }
            throw err;
        }
    };

    const confirmRemove = (id: number) => {
        const sym = (watchlistItems.find(it => it.id === id)?.stock?.symbol || '').toLowerCase();
        setStockToDelete({ id, symbol: sym });
        setDeleteModalOpen(true);
    };

    const handleRemoveStock = async () => {
        if (!stockToDelete) return;

        try {
            setIsLoading(true);
            await watchlistAPI.removeFromWatchlist(stockToDelete.id);
            await loadWatchlist();
            setDeleteModalOpen(false);
            setStockToDelete(null);
        } catch (err: any) {
            if (onAuthError && err.message && (
                err.message.includes('Authorization header required') ||
                err.message.includes('401') ||
                err.message.includes('Unauthorized')
            )) {
                onAuthError();
            } else {
                setError(err.message);
            }
        } finally {
            setIsLoading(false);
        }
    };

    const handleShowChart = async (item: WatchlistItem) => {
        const symbol = item.stock?.symbol || '';
        if (!symbol) return;
        
        setChartOpen(true);
        setIsChartLoading(true);
        
        // Set basic info first
        const currentPrice = latestQuotes[symbol]?.latest_price ?? item.current_price?.price ?? 0;
        const changePercent = latestQuotes[symbol]?.change_percent ?? item.current_price?.change_percent ?? 0;
        
        setSelectedStock({
            symbol: symbol,
            companyName: item.stock?.company_name || '',
            currentPrice: currentPrice,
            changePercent: changePercent,
        } as StockData);

        try {
            const res = await getPublicPredictions();
            if (res && res.items) {
                const found = res.items.find(i => i.best.symbol === symbol);
                if (found) {
                    const bestItemKey = found.best.best_prediction_item;
                    const contextLen = found.best.context_len;
                    const horizonLen = found.best.horizon_len;
                    const sortedChunks = (found.chunks || []).sort((a, b) => new Date(a.start_date).getTime() - new Date(b.start_date).getTime());
                    
                    let allDates: string[] = [];
                    let allActuals: number[] = [];
                    let allPreds: number[] = [];

                    sortedChunks.forEach(chunk => {
                        if (chunk.dates && chunk.dates.length > 0) {
                            allDates = allDates.concat(chunk.dates);
                            allActuals = allActuals.concat(chunk.actual_values || []);
                            const chunkPreds = chunk.predictions[bestItemKey] || [];
                            allPreds = allPreds.concat(chunkPreds as number[]);
                        }
                    });

                    if (allDates.length > 0) {
                         const lastActual = allActuals.length > 0 ? allActuals[allActuals.length - 1] : 0;
                         const lastPred = allPreds.length > 0 ? allPreds[allPreds.length - 1] : 0;
                         
                         // Logic from Dashboard.tsx to match display
                         const price = lastActual || lastPred;

                         // Calculate change based on first and last actual values
                         let startPrice = 0;
                         if (allActuals.length > 0) {
                             startPrice = allActuals[0];
                         }
                         const change = startPrice > 0 ? ((lastActual - startPrice) / startPrice) * 100 : 0;

                         // Calculate predicted change
                         let startPred = 0;
                         if (allPreds.length > 0) {
                             startPred = allPreds[0];
                         }
                         const predictedChange = startPred > 0 ? ((lastPred - startPred) / startPred) * 100 : 0;

                         // Calculate confidence
                         let confidence = 85;
                         try {
                             const metrics = JSON.parse(found.best.best_metrics);
                             if (metrics && typeof metrics.composite_score === 'number') {
                                 confidence = 100 - metrics.composite_score;
                             }
                         } catch (e) { }

                         setSelectedStock({
                             symbol: found.best.symbol,
                             companyName: found.best.short_name || found.best.symbol,
                             currentPrice: price,
                             changePercent: change,
                             predictedChangePercent: predictedChange,
                             prediction: {
                                 predicted_high: lastPred,
                                 predicted_low: lastPred,
                                 confidence: parseFloat(confidence.toFixed(4)),
                                 sentiment: predictedChange > 0 ? 'Bullish' : 'Bearish',
                                 analysis: '',
                                 modelName: bestItemKey,
                                 contextLen: contextLen,
                                 horizonLen: horizonLen,
                                 maxDeviationPercent: found.max_deviation_percent,
                                 chartData: {
                                     dates: allDates,
                                     actuals: allActuals,
                                     predictions: allPreds
                                 }
                             }
                         } as StockData);
                    }
                }
            }
        } catch (e) {
            console.error("Failed to fetch prediction for chart", e);
        } finally {
            setIsChartLoading(false);
        }
    };

    const filteredItems = watchlistItems.filter(item => {
        const matchesSearch = (item.stock?.symbol || '').toLowerCase().includes(searchTerm.toLowerCase()) ||
            (item.stock?.company_name || '').toLowerCase().includes(searchTerm.toLowerCase());
        // Default to 1 (stock) if stock_type is undefined
        const itemType = item.stock_type || 1;
        return matchesSearch && itemType === activeTab;
    });

    return (
        <div className="flex flex-col w-full">
            <div className="flex flex-wrap justify-between gap-3 p-4 mb-4">
                <div className="flex min-w-72 flex-col gap-2">
                    <p className="text-white text-4xl font-black leading-tight tracking-[-0.033em]">{t('watchlist.title')}</p>
                    <p className="text-white/60 text-base font-normal leading-normal">{t('watchlist.subtitle')}</p>
                </div>
            </div>

            {error && (
                <div
                    onClick={onAuthError}
                    className={`mx-4 mb-3 p-2 bg-red-500/10 border border-red-500/20 rounded-lg ${onAuthError ? 'cursor-pointer hover:bg-red-500/20 transition-colors' : ''}`}
                >
                    <p className="text-red-400 text-sm">
                        {(() => {
                            if (error.includes('symbol not found')) {
                                return t('addStock.errorNotFound');
                            }
                            if (error.includes('User not authenticated') || error.includes('Unauthorized')) {
                                return t('addStock.errorAuth');
                            }
                            return error;
                        })()}
                    </p>
                </div>
            )}

            <div className="flex space-x-1 mb-4 px-4 bg-white/5 rounded-lg p-1 mx-4 w-fit">
                <button
                    className={`px-6 py-2 rounded-md text-sm font-bold transition-all ${activeTab === 1 ? 'bg-primary text-black shadow-sm' : 'text-white/60 hover:text-white hover:bg-white/5'}`}
                    onClick={() => setActiveTab(1)}
                >
                    {t('watchlist.tabStock')}
                </button>
                <button
                    className={`px-6 py-2 rounded-md text-sm font-bold transition-all ${activeTab === 2 ? 'bg-primary text-black shadow-sm' : 'text-white/60 hover:text-white hover:bg-white/5'}`}
                    onClick={() => setActiveTab(2)}
                >
                    {t('watchlist.tabEtf')}
                </button>
            </div>

            <div className="px-4 py-2 mb-4 flex flex-col md:flex-row gap-3">
                <div className="flex flex-1 items-stretch rounded-lg h-14 border border-white/10 bg-white/5 focus-within:border-primary focus-within:ring-2 focus-within:ring-primary/50 transition-all duration-200">
                    <div className="text-white/60 flex items-center justify-center pl-4">
                        <span className="material-symbols-outlined">search</span>
                    </div>
                    <input
                        className="form-input flex w-full min-w-0 flex-1 resize-none overflow-hidden rounded-lg text-white focus:outline-0 focus:ring-0 border-none bg-transparent h-full placeholder:text-white/40 px-4 pl-2 text-base font-normal leading-normal"
                        placeholder={t('watchlist.searchPlaceholder')}
                        value={searchTerm}
                        onChange={e => setSearchTerm(e.target.value)}
                    />
                </div>

                <button
                    className="flex h-12 w-full md:w-auto items-center justify-center gap-2 px-5 rounded-lg bg-primary text-black text-sm font-bold hover:bg-opacity-90 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
                    onClick={() => setIsModalOpen(true)}
                    disabled={isLoading}
                >
                    <span className="material-symbols-outlined">add</span>
                    <span className="truncate">{t('watchlist.addStock')}</span>
                </button>
            </div>

            <AddStockModal
                isOpen={isModalOpen}
                onClose={() => setIsModalOpen(false)}
                onAdd={handleAddStock}
            />

            <ConfirmModal
                isOpen={deleteModalOpen}
                onClose={() => setDeleteModalOpen(false)}
                onConfirm={handleRemoveStock}
                title={t('modal.deleteTitle')}
                message={t('modal.deleteMessage').replace('{symbol}', stockToDelete?.symbol || '')}
                confirmText={t('modal.deleteConfirm')}
                cancelText={t('modal.deleteCancel')}
                isDanger={true}
                isLoading={isLoading}
            />

            {/* Chart Modal */}
            {chartOpen && selectedStock && (
                <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/80 backdrop-blur-sm p-4">
                    <div className="w-full max-w-5xl bg-card-dark border border-white/10 rounded-xl overflow-hidden flex flex-col max-h-[90vh]">
                         <div className="flex items-center justify-between p-6 border-b border-white/10">
                             <div>
                                 <h3 className="text-xl font-bold text-white">{selectedStock.companyName}</h3>
                                 <p className="text-sm text-white/60">{selectedStock.symbol}</p>
                             </div>
                             <button 
                                 onClick={() => setChartOpen(false)}
                                 className="p-2 rounded-full hover:bg-white/10 text-white/60 hover:text-white transition-colors"
                             >
                                 <span className="material-symbols-outlined">close</span>
                             </button>
                         </div>
                         <div className="p-6 overflow-y-auto flex-1 min-h-[300px] flex flex-col bg-card-dark">
                             {isChartLoading ? (
                                 <div className="flex-1 flex items-center justify-center">
                                     <div className="animate-spin rounded-full h-8 w-8 border-t-2 border-b-2 border-primary"></div>
                                 </div>
                             ) : (
                                 <>
                                     {/* Badges Row */}
                                     {selectedStock.prediction?.modelName && (
                                        <div className="flex flex-wrap gap-2 mb-6 overflow-x-auto no-scrollbar pb-2">
                                            {(() => {
                                                const isPositive = selectedStock.changePercent >= 0;
                                                const { hexColor, textClass } = getChangeColors(isPositive, language);
                                                const isPredPositive = (selectedStock.predictedChangePercent || 0) >= 0;
                                                const confidenceColor = selectedStock.prediction?.confidence ?? 0 > 85 ? 'text-primary' : (selectedStock.prediction?.confidence ?? 0) > 70 ? 'text-yellow-400' : 'text-red-400';

                                                return (
                                                    <>
                                                        <div className="flex flex-col rounded-lg border border-white/10 overflow-hidden h-fit w-[100px] shrink-0">
                                                            <div className="px-2 py-1 flex items-center gap-1.5 justify-center" style={{ backgroundColor: `${hexColor}33` }}>
                                                                <span className="material-symbols-outlined text-xs text-white/80">smart_toy</span>
                                                                <span className="text-xs font-medium text-white/80 leading-none">{t('prediction.model')}</span>
                                                            </div>
                                                            <div className="bg-white/5 px-2 py-1 flex justify-center">
                                                                <span className="text-xs font-bold text-white/90 leading-tight">{selectedStock.prediction?.modelName}</span>
                                                            </div>
                                                        </div>

                                                        <div className="flex flex-col rounded-lg border border-white/10 overflow-hidden h-fit w-[100px] shrink-0">
                                                            <div className="px-2 py-1 flex items-center gap-1.5 justify-center" style={{ backgroundColor: `${hexColor}33` }}>
                                                                <span className="material-symbols-outlined text-xs text-white/80">memory</span>
                                                                <span className="text-xs font-medium text-white/80 leading-none">{t('prediction.context')}</span>
                                                            </div>
                                                            <div className="bg-white/5 px-2 py-1 flex justify-center">
                                                                <span className="text-xs font-bold text-white/90 leading-tight">
                                                                    {selectedStock.prediction?.contextLen 
                                                                        ? (selectedStock.prediction.contextLen < 1024 
                                                                            ? selectedStock.prediction.contextLen 
                                                                            : Math.round(selectedStock.prediction.contextLen / 1024) + 'K') 
                                                                        : '?'}
                                                                </span>
                                                            </div>
                                                        </div>

                                                        <div className="flex flex-col rounded-lg border border-white/10 overflow-hidden h-fit w-[100px] shrink-0">
                                                            <div className="px-2 py-1 flex items-center gap-1.5 justify-center" style={{ backgroundColor: `${hexColor}33` }}>
                                                                <span className="material-symbols-outlined text-xs text-white/80">calendar_today</span>
                                                                <span className="text-xs font-medium text-white/80 leading-none">{t('prediction.horizon')}</span>
                                                            </div>
                                                            <div className="bg-white/5 px-2 py-1 flex justify-center">
                                                                <span className="text-xs font-bold text-white/90 leading-tight">
                                                                    {selectedStock.prediction?.horizonLen || '?'} {t('prediction.days')}
                                                                </span>
                                                            </div>
                                                        </div>

                                                        <div className="flex flex-col rounded-lg border border-white/10 overflow-hidden h-fit w-[100px] shrink-0">
                                                            <div className="px-2 py-1 flex items-center gap-1.5 justify-center" style={{ backgroundColor: `${hexColor}33` }}>
                                                                <span className="material-symbols-outlined text-xs text-white/80">query_stats</span>
                                                                <span className="text-xs font-medium text-white/80 leading-none">{t('prediction.maxDev')}</span>
                                                            </div>
                                                            <div className="bg-white/5 px-2 py-1 flex justify-center">
                                                                <span className="text-xs font-bold text-white/90 leading-tight">
                                                                    {selectedStock.prediction?.maxDeviationPercent?.toFixed(2) ?? '0.00'}%
                                                                </span>
                                                            </div>
                                                        </div>

                                                        <div className="flex flex-col rounded-lg border border-white/10 overflow-hidden h-fit w-[100px] shrink-0">
                                                            <div className="px-2 py-1 flex items-center gap-1.5 justify-center" style={{ backgroundColor: `${hexColor}33` }}>
                                                                <span className="material-symbols-outlined text-xs text-white/80">grade</span>
                                                                <span className="text-xs font-medium text-white/80 leading-none">{t('prediction.score')}</span>
                                                            </div>
                                                            <div className="bg-white/5 px-2 py-1 flex justify-center">
                                                                <span className={`text-xs font-bold leading-tight ${confidenceColor}`}>
                                                                    {(selectedStock.prediction?.confidence || 0).toFixed(4)}
                                                                </span>
                                                            </div>
                                                        </div>

                                                        <div className="flex flex-col rounded-lg border border-white/10 overflow-hidden h-fit w-[100px] shrink-0">
                                                            <div className="px-2 py-1 flex items-center gap-1.5 justify-center" style={{ backgroundColor: `${hexColor}33` }}>
                                                                <span className="material-symbols-outlined text-xs text-white/80">trending_up</span>
                                                                <span className="text-xs font-medium text-white/80 leading-none">{t('prediction.actChg')}</span>
                                                            </div>
                                                            <div className="bg-white/5 px-2 py-1 flex justify-center">
                                                                <span className={`text-xs font-bold leading-tight ${textClass}`}>
                                                                    {isPositive ? '+' : ''}{Math.abs(selectedStock.changePercent).toFixed(2)}%
                                                                </span>
                                                            </div>
                                                        </div>

                                                        {selectedStock.predictedChangePercent !== undefined && (
                                                            <div className="flex flex-col rounded-lg border border-white/10 overflow-hidden h-fit w-[100px] shrink-0">
                                                                <div className="px-2 py-1 flex items-center gap-1.5 justify-center" style={{ backgroundColor: `${hexColor}33` }}>
                                                                    <span className="material-symbols-outlined text-xs text-white/80">online_prediction</span>
                                                                    <span className="text-xs font-medium text-white/80 leading-none">{t('prediction.predChg')}</span>
                                                                </div>
                                                                <div className="bg-white/5 px-2 py-1 flex justify-center">
                                                                    <span className="text-xs font-bold leading-tight text-primary">
                                                                        {isPredPositive ? '+' : ''}{Math.abs(selectedStock.predictedChangePercent).toFixed(2)}%
                                                                    </span>
                                                                </div>
                                                            </div>
                                                        )}
                                                    </>
                                                );
                                            })()}
                                        </div>
                                     )}

                                     {/* Chart Section */}
                                     <div className="flex flex-1 min-h-[350px] flex-col gap-4 py-4">
                                        <PredictionChart 
                                            change={selectedStock.changePercent} 
                                            chartData={selectedStock.prediction?.chartData}
                                            currentPrice={selectedStock.currentPrice}
                                            startPrice={selectedStock.currentPrice / (1 + selectedStock.changePercent / 100)}
                                        />
                                     </div>

                                     {/* Fallback/Empty State */}
                                     {!selectedStock.prediction && (
                                         <div className="flex flex-col items-center justify-center text-center gap-2 py-12">
                                            <div className="w-5 h-5 border-2 border-dashed rounded-full animate-spin border-primary"></div>
                                            <span className="text-xs text-white/60">{t('watchlist.noPredictionData') || "No prediction data available."}</span>
                                        </div>
                                     )}
                                 </>
                             )}
                         </div>
                    </div>
                </div>
            )}

            {watchlistItems.length > 0 ? (
                <div className="px-4 py-2 @container">
                    <div className="flex overflow-hidden rounded-xl border border-[#2D2D2D] bg-black/20">
                        <table className="flex-1">
                            <thead className="border-b border-b-[#2D2D2D]">
                                <tr>
                                    <th className="px-4 py-3 text-left text-white/60 text-sm font-medium leading-normal">{t('watchlist.ticker')}</th>
                                    <th className="px-4 py-3 text-left text-white/60 text-sm font-medium leading-normal">{t('watchlist.latestDate')}</th>
                                    <th className="px-4 py-3 text-left text-white/60 text-sm font-medium leading-normal hidden sm:table-cell">{t('watchlist.lastPrice')}</th>
                                    <th className="px-4 py-3 text-left text-white/60 text-sm font-medium leading-normal">{t('watchlist.todayChange')}</th>
                                    <th className="px-4 py-3 text-left text-white/60 text-sm font-medium leading-normal">{t('watchlist.turnoverRate')}</th>
                                    <th className="px-4 py-3 text-right text-white/60 text-sm font-medium leading-normal">{t('watchlist.actions')}</th>
                                </tr>
                            </thead>
                            <tbody>
                                {filteredItems.map(item => {
                                    const changePercent = (latestQuotes[item.stock?.symbol || '']?.change_percent ?? item.current_price?.change_percent) || 0;
                                    const isPositive = changePercent >= 0;
                                    const { textClass } = getChangeColors(isPositive, language);
                                    const currentPrice = latestQuotes[item.stock?.symbol || '']?.latest_price ?? item.current_price?.price;

                                    return (
                                        <tr key={item.id} className="border-t border-t-[#2D2D2D]">
                                            <td className="h-[72px] px-4 py-2 text-white text-sm font-normal leading-normal">
                                                <span className="font-bold">{(item.stock?.symbol || '').toLowerCase()}</span><br />
                                                <span className="text-xs text-white/60">{item.stock?.company_name}</span>
                                            </td>
                                            <td className="h-[72px] px-4 py-2 text-white/60 text-sm">
                                                {latestQuotes[item.stock?.symbol || '']?.trading_date || '—'}
                                            </td>
                                            <td className="h-[72px] px-4 py-2 text-white/80 text-sm font-normal leading-normal hidden sm:table-cell">
                                                {currentPrice != null ? currentPrice.toFixed(2) : '—'}
                                            </td>
                                            <td className={`h-[72px] px-4 py-2 text-sm font-normal leading-normal ${textClass}`}>
                                                {currentPrice != null && changePercent != null ? (
                                                    <>
                                                        {isPositive ? '+' : ''}{(currentPrice * changePercent / 100).toFixed(2)} ({isPositive ? '+' : ''}{changePercent.toFixed(2)}%)
                                                    </>
                                                ) : '—'}
                                            </td>
                                            <td className="h-[72px] px-4 py-2 text-white/60 text-sm">
                                                {latestQuotes[item.stock?.symbol || '']?.turnover_rate != null ? `${(latestQuotes[item.stock?.symbol || '']!.turnover_rate! * 100).toFixed(2)}%` : '—'}
                                            </td>
                                            <td className="h-[72px] px-4 py-2 text-white/40 text-sm font-bold leading-normal tracking-[0.015em] text-right">
                                                <button
                                                    onClick={() => handleShowChart(item)}
                                                    className="p-2 rounded-full hover:bg-white/10 text-primary transition-colors mr-1"
                                                    disabled={isLoading}
                                                    title={t('watchlist.showChart') || "Show Chart"}
                                                >
                                                    <span className="material-symbols-outlined" style={{ fontSize: '20px' }}>show_chart</span>
                                                </button>
                                                <button
                                                    onClick={() => confirmRemove(item.id)}
                                                    className="p-2 rounded-full hover:bg-white/10 text-red-500 transition-colors disabled:opacity-50"
                                                    disabled={isLoading}
                                                >
                                                    <span className="material-symbols-outlined" style={{ fontSize: '20px' }}>delete</span>
                                                </button>
                                            </td>
                                        </tr>
                                    );
                                })}
                            </tbody>
                        </table>
                    </div>
                </div>
            ) : (
                <div className="flex flex-col px-4 py-16 mt-8">
                    <div className="flex flex-col items-center gap-6">
                        <div className="text-primary">
                            <span className="material-symbols-outlined" style={{ fontSize: '96px' }}>playlist_add</span>
                        </div>
                        <div className="flex max-w-[480px] flex-col items-center gap-2">
                            <p className="text-white text-lg font-bold leading-tight tracking-[-0.015em] max-w-[480px] text-center">{t('watchlist.emptyTitle')}</p>
                            <p className="text-white/60 text-sm font-normal leading-normal max-w-[480px] text-center">{t('watchlist.emptySubtitle')}</p>
                        </div>
                    </div>
                </div>
            )}
        </div>
    );
};

export default Watchlist;

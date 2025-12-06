
import React, { useState, useEffect } from 'react';
import { StockData } from '../../types';
import StockPredictionCard from './StockPredictionCard';
import AddStockModal from './AddStockModal';
import { useLanguage } from '../../contexts/LanguageContext';
import { watchlistAPI, getPublicPredictions } from '../../services/apiService';

interface DashboardProps {
    stocks: StockData[];
    isLoading: boolean;
    error: string | null;
    onRefresh?: () => void;
}

const FilterChip: React.FC<{ label: string; active?: boolean; onClick: () => void; }> = ({ label, active, onClick }) => (
    <div
        onClick={onClick}
        className={`flex h-8 shrink-0 items-center justify-center gap-x-2 rounded-full px-4 cursor-pointer transition-colors ${active ? 'bg-primary/20 text-primary' : 'bg-white/10 text-white/80 hover:bg-white/20'
            }`}
    >
        <p className="text-sm font-medium leading-normal">{label}</p>
    </div>
);


const Dashboard: React.FC<DashboardProps> = ({ stocks: propStocks, isLoading: propIsLoading, error: propError, onRefresh }) => {
    const { t, language } = useLanguage();
    const [activeFilter, setActiveFilter] = useState('All');
    const [activeHorizon, setActiveHorizon] = useState<3 | 7>(3);
    const [isModalOpen, setIsModalOpen] = useState(false);
    const filters = ['All', 'Highest Confidence', 'Potential Growth', 'Bullish', 'Bearish'];
    
    const [publicStocks, setPublicStocks] = useState<StockData[]>([]);
    const [isFetching, setIsFetching] = useState(true);
    const [fetchError, setFetchError] = useState<string | null>(null);

    useEffect(() => {
        const fetchPublic = async () => {
            setIsFetching(true);
            setFetchError(null);
            try {
                const res = await getPublicPredictions(activeHorizon);
                if (res && res.items) {
                     const mapped = res.items.map(item => {
                        const bestItemKey = item.best.best_prediction_item;
                        const contextLen = item.best.context_len;
                        const horizonLen = item.best.horizon_len;
                        // Sort chunks by date ascending (oldest first)
                        const sortedChunks = (item.chunks || []).sort((a, b) => new Date(a.start_date).getTime() - new Date(b.start_date).getTime());
                        
                        let allDates: string[] = [];
                        let allActuals: number[] = [];
                        let allPreds: number[] = [];

                        sortedChunks.forEach(chunk => {
                            if (chunk.dates && chunk.dates.length > 0) {
                                allDates = allDates.concat(chunk.dates);
                                allActuals = allActuals.concat(chunk.actual_values || []);
                                const chunkPreds = chunk.predictions[bestItemKey] || [];
                                allPreds = allPreds.concat(chunkPreds);
                            }
                        });

                        if (allDates.length === 0) return null;

                        const lastActual = allActuals.length > 0 ? allActuals[allActuals.length - 1] : 0;
                        const lastPred = allPreds.length > 0 ? allPreds[allPreds.length - 1] : 0;
                        const lastDate = allDates.length > 0 ? allDates[allDates.length - 1] : "";

                        // If no actual data (future forecast), use pred as current? Or 0?
                        // Let's assume there is some actual data, or we use pred as "Target"
                        const price = lastActual || lastPred;
                        
                        // Calculate change based on first and last actual values of the chunks
                        let startPrice = 0;
                        if (allActuals.length > 0) {
                            startPrice = allActuals[0];
                        }
                        const endPrice = lastActual;
                        const change = startPrice > 0 ? ((endPrice - startPrice) / startPrice) * 100 : 0;

                        // Calculate predicted change
                        let startPred = 0;
                        if (allPreds.length > 0) {
                            startPred = allPreds[0];
                        }
                        const endPred = lastPred;
                        const predictedChange = startPred > 0 ? ((endPred - startPred) / startPred) * 100 : 0;

                        // Calculate confidence from best_metrics
                        let confidence = 85;
                        try {
                            const metrics = JSON.parse(item.best.best_metrics);
                            if (metrics && typeof metrics.composite_score === 'number') {
                                confidence = 100 - metrics.composite_score;
                            }
                        } catch (e) {
                            // Keep default
                        }

                        return {
                            symbol: item.best.symbol,
                            companyName: item.best.short_name || item.best.symbol,
                            currentPrice: price,
                            changePercent: change,
                            predictedChangePercent: predictedChange,
                            prediction: {
                                predicted_high: lastPred,
                                predicted_low: lastPred,
                                confidence: parseFloat(confidence.toFixed(4)),
                                sentiment: change > 0 ? 'Bullish' : 'Bearish',
                                analysis: language === 'zh' 
                                    ? `最佳模型: ${bestItemKey} 上下文: ${contextLen ? (contextLen < 1024 ? contextLen : Math.round(contextLen / 1024) + 'K') : '?'} 预测: ${horizonLen || '?'}天`
                                    : `Best: ${bestItemKey} Ctx: ${contextLen ? (contextLen < 1024 ? contextLen : Math.round(contextLen / 1024) + 'K') : '?'} Hor: ${horizonLen || '?'}d`,
                                modelName: bestItemKey,
                                contextLen: contextLen,
                                horizonLen: horizonLen,
                                maxDeviationPercent: item.max_deviation_percent,
                                chartData: {
                                    dates: allDates,
                                    actuals: allActuals,
                                    predictions: allPreds
                                }
                            }
                        } as StockData;
                    }).filter((item): item is StockData => item !== null);
                    setPublicStocks(mapped);
                }
            } catch (e: any) {
                console.error("Fetch error", e);
                setFetchError(e.message || "Failed to load public predictions");
            } finally {
                setIsFetching(false);
            }
        };
        fetchPublic();
    }, [language, activeHorizon]);

    const handleAddStock = async (symbol: string, type: 1 | 2 = 1) => {
        await watchlistAPI.addToWatchlist({ symbol, stock_type: type });
        // Refresh dashboard after adding stock
        if (onRefresh) {
            onRefresh();
        }
    };

    const displayStocks = publicStocks;
    const isLoading = isFetching;
    const error = propError || fetchError;

    const filteredStocks = displayStocks.filter(stock => {
        if (!stock.prediction) return activeFilter === 'All';
        switch (activeFilter) {
            case 'Highest Confidence':
                return stock.prediction.confidence > 85;
            case 'Potential Growth':
                return (stock.prediction.predicted_high / stock.currentPrice - 1) * 100 > 5;
            case 'Bullish':
                return stock.prediction.sentiment === 'Bullish';
            case 'Bearish':
                return stock.prediction.sentiment === 'Bearish';
            default:
                return true;
        }
    });

    return (
        <div className="flex flex-col gap-6">
            <header className="flex flex-wrap justify-between gap-4 items-center">
                <div className="flex flex-col gap-1">
                    <h1 className="text-white text-4xl font-black leading-tight tracking-[-0.033em]">{t('dashboard.title')}</h1>
                    <p className="text-white/60 text-base font-normal leading-normal">{t('dashboard.subtitle')}</p>
                </div>
            </header>
            <div className="flex flex-col gap-4">
                <div className="flex flex-wrap justify-between gap-2 items-center">
                    <div className="flex space-x-1 bg-white/5 rounded-lg p-1">
                        <button
                            onClick={() => setActiveHorizon(3)}
                            className={`px-6 py-2 rounded-md text-sm font-bold transition-all ${activeHorizon === 3 ? 'bg-primary text-black shadow-sm' : 'text-white/60 hover:text-white hover:bg-white/5'}`}
                        >
                            P-3
                        </button>
                        <button
                            onClick={() => setActiveHorizon(7)}
                            className={`px-6 py-2 rounded-md text-sm font-bold transition-all ${activeHorizon === 7 ? 'bg-primary text-black shadow-sm' : 'text-white/60 hover:text-white hover:bg-white/5'}`}
                        >
                            P-7
                        </button>
                    </div>
                    <button
                        onClick={() => setIsModalOpen(true)}
                        className="flex items-center justify-center gap-2 px-4 h-10 rounded-lg bg-primary text-background-dark text-sm font-bold leading-normal tracking-[0.015em] hover:opacity-90 transition-opacity"
                    >
                        <span className="material-symbols-outlined" style={{ fontVariationSettings: "'FILL' 1" }}>add</span>
                        <span className="truncate">{t('dashboard.addStock')}</span>
                    </button>
                </div>
                <div className="flex gap-3 overflow-x-auto pb-2 -mx-1 px-1 hidden">
                    {filters.map(filter => (
                        <FilterChip
                            key={filter}
                            label={t(`dashboard.filters.${filter.replace(/\s+/g, '').charAt(0).toLowerCase() + filter.replace(/\s+/g, '').slice(1)}`)}
                            active={activeFilter === filter}
                            onClick={() => setActiveFilter(filter)}
                        />
                    ))}
                </div>
            </div>

            {error && (
                <div className="bg-red-900/50 border border-red-500/50 text-red-300 p-4 rounded-lg text-center">
                    <p className="font-bold">{t('dashboard.errorTitle')}</p>
                    <p className="text-sm">{error}</p>
                </div>
            )}

            <div className="grid grid-cols-1 gap-6">
                {isLoading ? (
                    Array.from({ length: 6 }).map((_, index) => (
                        <div key={index} className="flex flex-col gap-4 rounded-xl border border-white/10 bg-card-dark p-6 min-h-[350px] animate-pulse">
                            <div className="flex justify-between items-start">
                                <div>
                                    <div className="h-6 w-16 bg-white/10 rounded"></div>
                                    <div className="h-4 w-24 bg-white/10 rounded mt-2"></div>
                                </div>
                                <div>
                                    <div className="h-8 w-20 bg-white/10 rounded"></div>
                                    <div className="h-4 w-12 bg-white/10 rounded mt-2 ml-auto"></div>
                                </div>
                            </div>
                            <div className="flex-1 bg-white/5 rounded-lg"></div>
                            <div className="h-4 w-full bg-white/10 rounded"></div>
                            <div className="flex justify-between items-center">
                                <div className="h-4 w-1/3 bg-white/10 rounded"></div>
                                <div className="h-4 w-1/4 bg-white/10 rounded"></div>
                            </div>
                        </div>
                    ))
                ) : (
                    filteredStocks.map(stock => <StockPredictionCard key={stock.symbol} stock={stock} onAddToWatchlist={handleAddStock} />)
                )}
            </div>
            {!isLoading && filteredStocks.length === 0 && (
                <div className="text-center col-span-full py-12 bg-card-dark rounded-xl">
                    <p className="text-white/80">{t('dashboard.noStocks')}</p>
                </div>
            )}

            <AddStockModal
                isOpen={isModalOpen}
                onClose={() => setIsModalOpen(false)}
                onAdd={handleAddStock}
            />
        </div>
    );
};

export default Dashboard;

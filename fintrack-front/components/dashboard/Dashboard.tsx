
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
    const { t } = useLanguage();
    const [activeFilter, setActiveFilter] = useState('All');
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
                const res = await getPublicPredictions();
                if (res && res.items) {
                     const mapped = res.items.map(item => {
                        const bestItemKey = item.best.best_prediction_item;
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
                        // Calculate change based on the last chunk or overall trend? 
                        // Typically daily change or change from previous day.
                        // Let's use the last two actuals if available, or last actual vs last pred.
                        // Existing logic: const change = lastActual > 0 ? ((lastPred - lastActual) / lastActual) * 100 : 0;
                        // This compares last prediction with last actual. This implies the prediction is "next step" relative to actual?
                        // But in the chunks, actual and prediction are for the same dates (validation).
                        // So `lastPred` corresponds to `lastActual` in time (roughly).
                        // The user wants to show "Trend".
                        // Let's stick to the previous logic for `changePercent` for now to avoid breaking UI logic, 
                        // but maybe we should compare last actual with previous actual for "daily change"?
                        // For now, I'll keep the logic: ((lastPred - lastActual) / lastActual) * 100
                        const change = lastActual > 0 ? ((lastPred - lastActual) / lastActual) * 100 : 0;

                        return {
                            symbol: item.best.symbol,
                            companyName: item.best.short_name || item.best.symbol,
                            currentPrice: price,
                            changePercent: change,
                            prediction: {
                                predicted_high: lastPred,
                                predicted_low: lastPred,
                                confidence: 85,
                                sentiment: change > 0 ? 'Bullish' : 'Bearish',
                                analysis: `Forecast for ${lastDate} (Best: ${bestItemKey})`,
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
    }, []);

    const handleAddStock = async (symbol: string) => {
        await watchlistAPI.addToWatchlist(symbol);
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
                    <div className="flex gap-2">
                        <button className="flex items-center justify-center p-2 rounded-lg text-white/80 bg-white/5 hover:bg-white/10 transition-colors">
                            <span className="material-symbols-outlined text-xl">calendar_today</span>
                        </button>
                        <button className="flex items-center justify-center p-2 rounded-lg text-white/80 bg-white/5 hover:bg-white/10 transition-colors">
                            <span className="material-symbols-outlined text-xl">sort</span>
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
                            label={t(`dashboard.filter${filter.replace(/\s+/g, '')}`)}
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
                    filteredStocks.map(stock => <StockPredictionCard key={stock.symbol} stock={stock} />)
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

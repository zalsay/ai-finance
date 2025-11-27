
import React, { useState } from 'react';
import { StockData } from '../../types';
import StockPredictionCard from './StockPredictionCard';
import AddStockModal from './AddStockModal';
import { useLanguage } from '../../contexts/LanguageContext';
import { watchlistAPI } from '../../services/apiService';

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


const Dashboard: React.FC<DashboardProps> = ({ stocks, isLoading, error, onRefresh }) => {
    const { t } = useLanguage();
    const [activeFilter, setActiveFilter] = useState('All');
    const [isModalOpen, setIsModalOpen] = useState(false);
    const filters = ['All', 'Highest Confidence', 'Potential Growth', 'Bullish', 'Bearish'];

    const handleAddStock = async (symbol: string) => {
        await watchlistAPI.addToWatchlist(symbol);
        // Refresh dashboard after adding stock
        if (onRefresh) {
            onRefresh();
        }
    };

    const filteredStocks = stocks.filter(stock => {
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
                <div className="flex gap-3 overflow-x-auto pb-2 -mx-1 px-1">
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

            <div className="grid grid-cols-1 lg:grid-cols-2 xl:grid-cols-3 gap-6">
                {isLoading && !stocks.some(s => s.prediction) ? (
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

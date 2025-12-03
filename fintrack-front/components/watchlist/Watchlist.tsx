
import React, { useState, useEffect } from 'react';
import { StockData } from '../../types';
import { useLanguage } from '../../contexts/LanguageContext';
import { getChangeColors } from '../../utils/colorUtils';
import { watchlistAPI, WatchlistItem } from '../../services/apiService';

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
    const [searchTerm, setSearchTerm] = useState('');
    const [newSymbol, setNewSymbol] = useState('');
    const [isLoading, setIsLoading] = useState(false);
    const [error, setError] = useState<string | null>(null);

    useEffect(() => {
        loadWatchlist();
    }, []);

    const loadWatchlist = async () => {
        try {
            setIsLoading(true);
            const response = await watchlistAPI.getWatchlist();
            setWatchlistItems(response.watchlist);
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

    const addStock = async () => {
        if (!newSymbol.trim()) return;
        
        try {
            setIsLoading(true);
            await watchlistAPI.addToWatchlist(newSymbol.toUpperCase());
            setNewSymbol('');
            await loadWatchlist(); // 重新加载列表
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

    const removeStock = async (id: number) => {
        try {
            setIsLoading(true);
            await watchlistAPI.removeFromWatchlist(id);
            await loadWatchlist(); // 重新加载列表
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
    
    const filteredItems = watchlistItems.filter(item => 
        item.symbol.toLowerCase().includes(searchTerm.toLowerCase()) || 
        item.company_name.toLowerCase().includes(searchTerm.toLowerCase())
    );

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
                className={`mx-4 mb-4 p-3 bg-red-500/10 border border-red-500/20 rounded-lg ${onAuthError ? 'cursor-pointer hover:bg-red-500/20 transition-colors' : ''}`}
            >
                <p className="text-red-400 text-sm">{error}</p>
            </div>
        )}
        
        <div className="px-4 py-3 mb-6">
            <div className="flex w-full flex-1 items-stretch rounded-lg h-14 border border-white/10 bg-white/5 focus-within:border-primary focus-within:ring-2 focus-within:ring-primary/50 transition-all duration-200">
                <div className="text-white/60 flex items-center justify-center pl-4">
                    <span className="material-symbols-outlined">search</span>
                </div>
                <input 
                    className="form-input flex w-full min-w-0 flex-1 resize-none overflow-hidden rounded-lg text-white focus:outline-0 focus:ring-0 border-none bg-transparent h-full placeholder:text-white/40 px-4 pl-2 text-base font-normal leading-normal" 
                    placeholder={t('watchlist.searchPlaceholder')}
                    value={searchTerm}
                    onChange={e => setSearchTerm(e.target.value)}
                />
                <input 
                    className="form-input flex min-w-0 resize-none overflow-hidden rounded-lg text-white focus:outline-0 focus:ring-0 border-none bg-transparent h-full placeholder:text-white/40 px-2 text-base font-normal leading-normal" 
                    placeholder="股票代码"
                    value={newSymbol}
                    onChange={e => setNewSymbol(e.target.value)}
                    onKeyPress={e => e.key === 'Enter' && addStock()}
                    disabled={isLoading}
                />
                <button 
                    className="flex m-2 min-w-[84px] max-w-[480px] cursor-pointer items-center justify-center overflow-hidden rounded-md h-auto px-4 bg-primary text-black text-sm font-bold leading-normal tracking-[0.015em] hover:bg-opacity-90 transition-colors disabled:opacity-50 disabled:cursor-not-allowed" 
                    onClick={addStock}
                    disabled={isLoading || !newSymbol.trim()}
                >
                    <span className="truncate">{isLoading ? '添加中...' : t('watchlist.addStock')}</span>
                </button>
            </div>
        </div>

        {watchlistItems.length > 0 ? (
            <div className="px-4 py-3 @container">
                <div className="flex overflow-hidden rounded-xl border border-[#2D2D2D] bg-black/20">
                    <table className="flex-1">
                        <thead className="border-b border-b-[#2D2D2D]">
                            <tr>
                                <th className="px-4 py-3 text-left text-white/60 text-sm font-medium leading-normal">{t('watchlist.tickerCompany')}</th>
                                <th className="px-4 py-3 text-left text-white/60 text-sm font-medium leading-normal hidden sm:table-cell">{t('watchlist.lastPrice')}</th>
                                <th className="px-4 py-3 text-left text-white/60 text-sm font-medium leading-normal">{t('watchlist.todayChange')}</th>
                                <th className="px-4 py-3 text-left text-white/60 w-32 text-sm font-medium leading-normal hidden md:table-cell">{t('watchlist.chart')}</th>
                                <th className="px-4 py-3 text-right text-white/60 text-sm font-medium leading-normal">{t('watchlist.actions')}</th>
                            </tr>
                        </thead>
                        <tbody>
                            {filteredItems.map(item => {
                                const changePercent = item.change_percent || 0;
                                const isPositive = changePercent >= 0;
                                const { textClass } = getChangeColors(isPositive, language);
                                return (
                                    <tr key={item.id} className="border-t border-t-[#2D2D2D]">
                                        <td className="h-[72px] px-4 py-2 text-white text-sm font-normal leading-normal">
                                            <span className="font-bold">{item.symbol}</span><br/>
                                            <span className="text-xs text-white/60">{item.company_name}</span>
                                        </td>
                                        <td className="h-[72px] px-4 py-2 text-white/80 text-sm font-normal leading-normal hidden sm:table-cell">
                                            ${item.current_price ? item.current_price.toFixed(2) : 'N/A'}
                                        </td>
                                        <td className={`h-[72px] px-4 py-2 text-sm font-normal leading-normal ${textClass}`}>
                                            {item.current_price && changePercent ? (
                                                <>
                                                    {isPositive ? '+' : ''}{(item.current_price * changePercent / 100).toFixed(2)} ({isPositive ? '+' : ''}{changePercent.toFixed(2)}%)
                                                </>
                                            ) : 'N/A'}
                                        </td>
                                        <td className="h-[72px] px-4 py-2 w-32 text-sm font-normal leading-normal hidden md:table-cell">
                                            <Sparkline change={changePercent} />
                                        </td>
                                        <td className="h-[72px] px-4 py-2 text-white/40 text-sm font-bold leading-normal tracking-[0.015em] text-right">
                                            <button 
                                                onClick={() => removeStock(item.id)} 
                                                className="p-2 rounded-full hover:bg-white/10 hover:text-white transition-colors disabled:opacity-50"
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

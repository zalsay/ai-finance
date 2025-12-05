
import React, { useState } from 'react';
import { StockData } from '../../types';
import { useLanguage } from '../../contexts/LanguageContext';
import { getChangeColors } from '../../utils/colorUtils';
import PredictionChart from '../common/PredictionChart';

interface StockPredictionCardProps {
  stock: StockData;
  onAddToWatchlist?: (symbol: string) => void;
}

const StockPredictionCard: React.FC<StockPredictionCardProps> = ({ stock, onAddToWatchlist }) => {
    const { language, t } = useLanguage();
    const isPositive = stock.changePercent >= 0;
    const { textClass, hexColor } = getChangeColors(isPositive, language); // Destructure hexColor
    
    const isPredPositive = (stock.predictedChangePercent || 0) >= 0;
    const { textClass: predTextClass } = getChangeColors(isPredPositive, language);

    const confidenceColor = stock.prediction?.confidence ?? 0 > 85 ? 'text-primary' : (stock.prediction?.confidence ?? 0) > 70 ? 'text-yellow-400' : 'text-red-400';
    
    const [isAdded, setIsAdded] = useState(false);

    const startPrice = stock.currentPrice / (1 + stock.changePercent / 100);

    return (
        <div className="flex flex-col gap-4 rounded-xl border border-white/10 bg-card-dark p-6">
            <div className="flex flex-wrap md:flex-nowrap justify-between items-start gap-x-3 gap-y-3">
                <div>
                    <p className="text-white text-lg font-bold leading-normal">{stock.companyName}</p>
                    <p className="text-white/60 text-sm truncate max-w-[150px]">{stock.symbol}</p>
                </div>
                {stock.prediction?.modelName && (
                    <div className="flex gap-2 w-full md:w-auto order-3 md:order-none overflow-x-auto no-scrollbar">
                        <div className="flex flex-col rounded-lg border border-white/10 overflow-hidden h-fit w-[100px] shrink-0">
                            <div className="px-2 py-1 flex items-center gap-1.5 justify-center" style={{ backgroundColor: `${hexColor}33` }}>
                                <span className="material-symbols-outlined text-xs text-white/80">smart_toy</span>
                                <span className="text-xs font-medium text-white/80 leading-none">{t('prediction.model')}</span>
                            </div>
                            <div className="bg-white/5 px-2 py-1 flex justify-center">
                                <span className="text-xs font-bold text-white/90 leading-tight">{stock.prediction.modelName}</span>
                            </div>
                        </div>

                        <div className="flex flex-col rounded-lg border border-white/10 overflow-hidden h-fit w-[100px] shrink-0">
                            <div className="px-2 py-1 flex items-center gap-1.5 justify-center" style={{ backgroundColor: `${hexColor}33` }}>
                                <span className="material-symbols-outlined text-xs text-white/80">memory</span>
                                <span className="text-xs font-medium text-white/80 leading-none">{t('prediction.context')}</span>
                            </div>
                            <div className="bg-white/5 px-2 py-1 flex justify-center">
                                <span className="text-xs font-bold text-white/90 leading-tight">
                                    {stock.prediction.contextLen 
                                        ? (stock.prediction.contextLen < 1024 
                                            ? stock.prediction.contextLen 
                                            : Math.round(stock.prediction.contextLen / 1024) + 'K') 
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
                                    {stock.prediction.horizonLen || '?'} {t('prediction.days')}
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
                                    {stock.prediction.maxDeviationPercent?.toFixed(2) ?? '0.00'}%
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
                                    {stock.prediction.confidence.toFixed(4)}
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
                                    {isPositive ? '+' : ''}{Math.abs(stock.changePercent).toFixed(2)}%
                                </span>
                            </div>
                        </div>

                        {stock.predictedChangePercent !== undefined && stock.predictedChangePercent !== 0 && (
                            <div className="flex flex-col rounded-lg border border-white/10 overflow-hidden h-fit w-[100px] shrink-0">
                                <div className="px-2 py-1 flex items-center gap-1.5 justify-center" style={{ backgroundColor: `${hexColor}33` }}>
                                    <span className="material-symbols-outlined text-xs text-white/80">online_prediction</span>
                                    <span className="text-xs font-medium text-white/80 leading-none">{t('prediction.predChg')}</span>
                                </div>
                                <div className="bg-white/5 px-2 py-1 flex justify-center">
                                    <span className="text-xs font-bold leading-tight text-primary">
                                        {isPredPositive ? '+' : ''}{Math.abs(stock.predictedChangePercent).toFixed(2)}%
                                    </span>
                                </div>
                            </div>
                        )}
                    </div>
                )}
                <div className="flex items-center gap-3 ml-auto order-2 md:order-none">
                    {onAddToWatchlist && (
                        <button 
                            onClick={() => {
                                onAddToWatchlist(stock.symbol);
                                setIsAdded(true);
                                setTimeout(() => setIsAdded(false), 2000);
                            }}
                            className={`flex items-center justify-center w-10 h-10 rounded-lg bg-white/5 hover:bg-primary hover:text-black transition-colors ${isAdded ? 'text-green-400' : 'text-white/60'}`}
                            title={isAdded ? t('Added!', '已添加！') : t('Add to Watchlist', '加入关注')}
                        >
                            <div className="relative flex items-center justify-center">
                                <span className="material-symbols-outlined">{isAdded ? 'check' : 'favorite'}</span>
                                {!isAdded && <span className="absolute -top-1 -right-2 text-[10px] leading-none font-bold">+</span>}
                            </div>
                        </button>
                    )}
                </div>
            </div>
            <div className="flex min-h-[150px] md:min-h-[180px] flex-1 flex-col gap-4 py-4">
                <PredictionChart 
                    change={stock.changePercent} 
                    chartData={stock.prediction?.chartData} 
                    currentPrice={stock.currentPrice}
                    startPrice={startPrice}
                />
            </div>
            
            {/* Legend Removed */}

            {stock.prediction ? (
                <>
                    {!stock.prediction.modelName && (
                        <p className="text-sm text-white/80">{stock.prediction.analysis}</p>
                    )}
                </>
            ) : (
                 <div className="flex flex-col items-center justify-center text-center gap-2">
                    <div className="w-5 h-5 border-2 border-dashed rounded-full animate-spin border-primary"></div>
                    <span className="text-xs text-white/60">{t('Awaiting AI prediction...', '等待 AI 预测...')}</span>
                </div>
            )}
        </div>
    );
};

export default StockPredictionCard;

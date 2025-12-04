import { StockData } from '../types';

export const mapPredictionResponseToStockData = (res: any, language: string): StockData[] => {
    if (!res || !res.items) return [];

    return res.items.map((item: any) => {
        const bestItemKey = item.best.best_prediction_item;
        const contextLen = item.best.context_len;
        const horizonLen = item.best.horizon_len;
        // Sort chunks by date ascending (oldest first)
        const sortedChunks = (item.chunks || []).sort((a: any, b: any) => new Date(a.start_date).getTime() - new Date(b.start_date).getTime());
        
        let allDates: string[] = [];
        let allActuals: number[] = [];
        let allPreds: number[] = [];

        sortedChunks.forEach((chunk: any) => {
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
    }).filter((item: any): item is StockData => item !== null);
};

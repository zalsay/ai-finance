
import React from 'react';
import { StockData } from '../../types';

interface StockPredictionCardProps {
  stock: StockData;
}

const Chart: React.FC<{ change: number }> = ({ change }) => {
    const isPositive = change >= 0;
    const color = isPositive ? "#32F08C" : "#F05454";
    // Static paths for visual representation
    const paths = {
      positive1: "M0 109C18.15 109 18.15 21 36.3 21C54.46 21 54.46 41 72.6 41C90.77 41 90.77 93 108.9 93C127.07 93 127.07 33 145.2 33C163.38 33 163.38 101 181.5 101C199.69 101 199.69 61 217.8 61C236 61 236 45 254.1 45C272.3 45 272.3 121 290.4 121C308.6 121 308.6 149 326.7 149C344.9 149 344.9 1 363 1C381.2 1 381.2 81 399.3 81C417.5 81 417.5 129 435.6 129C453.8 129 453.8 25 472 25",
      positive2: "M0 129C18.15 129 18.15 1 36.3 1C54.46 1 54.46 149 72.6 149C90.77 149 90.77 61 108.9 61C127.07 61 127.07 101 145.2 101C163.38 101 163.38 21 181.5 21C199.69 21 199.69 93 217.8 93C236 93 236 33 254.1 33C272.3 33 272.3 121 290.4 121C308.6 121 308.6 41 326.7 41C344.9 41 344.9 81 363 81C381.2 81 381.2 25 399.3 25C417.5 25 417.5 109 435.6 109C453.8 109 453.8 45 472 45",
      negative: "M0 45C18.15 45 18.15 121 36.3 121C54.46 121 54.46 101 72.6 101C90.77 101 90.77 61 108.9 61C127.07 61 127.07 93 145.2 93C163.38 93 163.38 33 181.5 33C199.69 33 199.69 61 217.8 61C236 61 236 21 254.1 21C272.3 21 272.3 81 290.4 81C308.6 81 308.6 1 326.7 1C344.9 1 344.9 149 363 149C381.2 149 381.2 109 399.3 109C417.5 109 417.5 41 435.6 41C453.8 41 453.8 129 472 129",
    };
    const pathData = isPositive ? (change > 1 ? paths.positive2 : paths.positive1) : paths.negative;

    return (
        <svg fill="none" height="100%" preserveAspectRatio="none" viewBox="-3 0 478 150" width="100%" xmlns="http://www.w3.org/2000/svg">
            <path d={`${pathData}V149H0Z`} fill={`url(#paint_${isPositive ? 'positive' : 'negative'})`}></path>
            <path d={pathData} stroke={color} strokeLinecap="round" strokeWidth="3"></path>
            <defs>
                <linearGradient gradientUnits="userSpaceOnUse" id={`paint_${isPositive ? 'positive' : 'negative'}`} x1="236" x2="236" y1="1" y2="149">
                    <stop stopColor={color} stopOpacity="0.3"></stop>
                    <stop offset="1" stopColor={color} stopOpacity="0"></stop>
                </linearGradient>
            </defs>
        </svg>
    )
};


const StockPredictionCard: React.FC<StockPredictionCardProps> = ({ stock }) => {
    const isPositive = stock.changePercent >= 0;
    const confidenceColor = stock.prediction?.confidence ?? 0 > 85 ? 'text-primary' : (stock.prediction?.confidence ?? 0) > 70 ? 'text-yellow-400' : 'text-red-400';

    return (
        <div className="flex flex-col gap-4 rounded-xl border border-white/10 bg-card-dark p-6">
            <div className="flex justify-between items-start">
                <div>
                    <p className="text-white text-lg font-bold leading-normal">{stock.symbol}</p>
                    <p className="text-white/60 text-sm truncate max-w-[150px]">{stock.companyName}</p>
                </div>
                <div>
                    <p className="text-white text-2xl font-bold leading-tight">${stock.currentPrice.toFixed(2)}</p>
                    <p className={`text-sm font-medium leading-normal text-right ${isPositive ? 'text-primary' : 'text-red-400'}`}>
                        {isPositive ? '+' : ''}{stock.changePercent.toFixed(2)}%
                    </p>
                </div>
            </div>
            <div className="flex min-h-[150px] md:min-h-[180px] flex-1 flex-col gap-4 py-4">
                <Chart change={stock.changePercent} />
            </div>
            {stock.prediction ? (
                <>
                    <p className="text-sm text-white/80">{stock.prediction.analysis}</p>
                    <div className="flex justify-between items-center text-white/60 text-xs">
                        <span>Predicted High: <strong className="text-white/80">${stock.prediction.predicted_high.toFixed(2)}</strong></span>
                        <span>Confidence: <strong className={confidenceColor}>{stock.prediction.confidence}%</strong></span>
                    </div>
                </>
            ) : (
                 <div className="flex flex-col items-center justify-center text-center gap-2">
                    <div className="w-5 h-5 border-2 border-dashed rounded-full animate-spin border-primary"></div>
                    <span className="text-xs text-white/60">Awaiting AI prediction...</span>
                </div>
            )}
        </div>
    );
};

export default StockPredictionCard;

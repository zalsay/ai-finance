import React, { useState } from 'react';
import { useLanguage } from '../../contexts/LanguageContext';

interface AddStockModalProps {
    isOpen: boolean;
    onClose: () => void;
    onAdd: (symbol: string, type: 1 | 2) => Promise<void>;
}

const AddStockModal: React.FC<AddStockModalProps> = ({ isOpen, onClose, onAdd }) => {
    const { t } = useLanguage();
    const [type, setType] = useState<1 | 2>(1);
    const [exchange, setExchange] = useState<'sh' | 'sz'>('sh');
    const [stockCode, setStockCode] = useState('');
    const [isLoading, setIsLoading] = useState(false);
    const [error, setError] = useState<string | null>(null);

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault();
        setError(null);

        // Validate stock code
        if (!stockCode || stockCode.length !== 6) {
            setError('请输入6位股票代码');
            return;
        }

        if (!/^\d{6}$/.test(stockCode)) {
            setError('股票代码只能包含数字');
            return;
        }

        setIsLoading(true);
        try {
            const fullSymbol = `${exchange}${stockCode}`;
            await onAdd(fullSymbol, type);
            // Reset form on success
            setStockCode('');
            setExchange('sh');
            onClose();
        } catch (err: any) {
            setError(err.message || '添加股票失败');
        } finally {
            setIsLoading(false);
        }
    };

    const handleClose = () => {
        if (!isLoading) {
            setStockCode('');
            setExchange('sh');
            setType(1);
            setError(null);
            onClose();
        }
    };

    if (!isOpen) return null;

    return (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/60 backdrop-blur-sm">
            <div className="w-full max-w-md bg-card-dark rounded-xl shadow-2xl border border-white/10 overflow-hidden">
                {/* Header */}
                <div className="px-6 py-4 border-b border-white/10 flex items-center justify-between">
                    <h2 className="text-xl font-bold text-white">添加股票</h2>
                    <button
                        onClick={handleClose}
                        disabled={isLoading}
                        className="text-white/60 hover:text-white transition-colors disabled:opacity-50"
                    >
                        <svg className="w-6 h-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                        </svg>
                    </button>
                </div>

                {/* Body */}
                <form onSubmit={handleSubmit} className="p-6 space-y-4">
                    {/* Type Selection */}
                    <div className="flex flex-col">
                        <label className="text-white/80 text-sm font-medium mb-2">类型</label>
                        <div className="flex gap-3">
                            <button
                                type="button"
                                onClick={() => setType(1)}
                                disabled={isLoading}
                                className={`flex-1 px-4 py-3 rounded-lg font-medium transition-colors ${type === 1
                                        ? 'bg-primary text-background-dark'
                                        : 'bg-white/5 text-white/60 hover:bg-white/10 hover:text-white'
                                    } disabled:opacity-50`}
                            >
                                股票
                            </button>
                            <button
                                type="button"
                                onClick={() => setType(2)}
                                disabled={isLoading}
                                className={`flex-1 px-4 py-3 rounded-lg font-medium transition-colors ${type === 2
                                        ? 'bg-primary text-background-dark'
                                        : 'bg-white/5 text-white/60 hover:bg-white/10 hover:text-white'
                                    } disabled:opacity-50`}
                            >
                                ETF基金
                            </button>
                        </div>
                    </div>

                    {/* Exchange Selection */}
                    <div className="flex flex-col">
                        <label className="text-white/80 text-sm font-medium mb-2">交易所</label>
                        <div className="flex gap-3">
                            <button
                                type="button"
                                onClick={() => setExchange('sh')}
                                disabled={isLoading}
                                className={`flex-1 px-4 py-3 rounded-lg font-medium transition-colors ${exchange === 'sh'
                                        ? 'bg-primary text-background-dark'
                                        : 'bg-white/5 text-white/60 hover:bg-white/10 hover:text-white'
                                    } disabled:opacity-50`}
                            >
                                沪市 (sh)
                            </button>
                            <button
                                type="button"
                                onClick={() => setExchange('sz')}
                                disabled={isLoading}
                                className={`flex-1 px-4 py-3 rounded-lg font-medium transition-colors ${exchange === 'sz'
                                        ? 'bg-primary text-background-dark'
                                        : 'bg-white/5 text-white/60 hover:bg-white/10 hover:text-white'
                                    } disabled:opacity-50`}
                            >
                                深市 (sz)
                            </button>
                        </div>
                    </div>

                    {/* Stock Code Input */}
                    <div className="flex flex-col">
                        <label className="text-white/80 text-sm font-medium mb-2">
                            股票代码
                            <span className="text-white/40 ml-2">(6位数字)</span>
                        </label>
                        <input
                            type="text"
                            value={stockCode}
                            onChange={(e) => setStockCode(e.target.value.replace(/\D/g, '').slice(0, 6))}
                            placeholder="例如: 600000"
                            disabled={isLoading}
                            className="w-full px-4 py-3 bg-white/5 border border-white/10 rounded-lg text-white placeholder:text-white/40 focus:outline-none focus:ring-2 focus:ring-primary/50 focus:border-transparent disabled:opacity-50"
                            maxLength={6}
                            autoFocus
                        />
                        <p className="text-white/40 text-xs mt-2">
                            完整代码: <span className="text-primary font-mono">{exchange}{stockCode || '______'}</span>
                        </p>
                    </div>

                    {/* Error Message */}
                    {error && (
                        <div className="p-3 bg-red-500/10 border border-red-500/20 rounded-lg">
                            <p className="text-red-400 text-sm">{error}</p>
                        </div>
                    )}

                    {/* Info Box */}
                    <div className="p-3 bg-blue-500/10 border border-blue-500/20 rounded-lg">
                        <p className="text-blue-300 text-xs">
                            添加成功后将自动同步该股票的历史数据
                        </p>
                    </div>

                    {/* Actions */}
                    <div className="flex gap-3 pt-2">
                        <button
                            type="button"
                            onClick={handleClose}
                            disabled={isLoading}
                            className="flex-1 px-4 py-3 bg-white/5 text-white rounded-lg font-medium hover:bg-white/10 transition-colors disabled:opacity-50"
                        >
                            取消
                        </button>
                        <button
                            type="submit"
                            disabled={isLoading || !stockCode || stockCode.length !== 6}
                            className="flex-1 px-4 py-3 bg-primary text-background-dark rounded-lg font-medium hover:bg-opacity-90 transition-colors disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center gap-2"
                        >
                            {isLoading ? (
                                <>
                                    <div className="w-4 h-4 border-2 border-background-dark border-t-transparent rounded-full animate-spin"></div>
                                    添加中...
                                </>
                            ) : (
                                `添加${type === 1 ? '股票' : 'ETF'}`
                            )}
                        </button>
                    </div>
                </form>
            </div>
        </div>
    );
};

export default AddStockModal;

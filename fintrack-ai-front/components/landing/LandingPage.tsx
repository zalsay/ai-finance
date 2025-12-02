import React from 'react';
import LogoIcon from '../icons/LogoIcon';
import { useLanguage } from '../../contexts/LanguageContext';

interface LandingPageProps {
    onLogin: () => void;
    onRegister: () => void;
}

const LandingPage: React.FC<LandingPageProps> = ({ onLogin, onRegister }) => {
    const { t } = useLanguage();

    return (
        <div className="min-h-screen bg-background-dark text-white font-display overflow-x-hidden">
            {/* Background Effects */}
            <div className="fixed inset-0 z-0 pointer-events-none">
                <div className="absolute top-[-10%] left-[-10%] w-[40%] h-[40%] bg-primary/20 rounded-full blur-[120px] opacity-30"></div>
                <div className="absolute bottom-[-10%] right-[-10%] w-[40%] h-[40%] bg-blue-500/20 rounded-full blur-[120px] opacity-30"></div>
            </div>

            {/* Header */}
            <header className="relative z-10 flex items-center justify-between px-6 py-6 md:px-12 lg:px-24 max-w-7xl mx-auto">
                <div className="flex items-center gap-3">
                    <LogoIcon className="w-8 h-8 text-primary" />
                    <span className="text-xl font-bold tracking-tight">FinTrack AI</span>
                </div>
                <div className="flex items-center gap-4">
                    <button 
                        onClick={onLogin}
                        className="text-sm font-medium text-white/80 hover:text-white transition-colors"
                    >
                        {t('login.signIn')}
                    </button>
                    <button 
                        onClick={onRegister}
                        className="px-5 py-2.5 text-sm font-bold bg-primary text-black rounded-full hover:bg-opacity-90 transition-all shadow-[0_0_15px_rgba(253,242,253,0.3)] hover:shadow-[0_0_25px_rgba(253,242,253,0.5)]"
                    >
                        {t('login.register')}
                    </button>
                </div>
            </header>

            {/* Hero Section */}
            <main className="relative z-10 flex flex-col items-center justify-center px-6 pt-20 pb-32 text-center md:pt-32 lg:pt-40 max-w-5xl mx-auto">
                <div className="inline-flex items-center gap-2 px-3 py-1 mb-8 rounded-full bg-white/5 border border-white/10 backdrop-blur-sm">
                    <span className="w-2 h-2 rounded-full bg-green-500 animate-pulse"></span>
                    <span className="text-xs font-medium text-white/70">AI-Powered Analysis</span>
                </div>
                
                <h1 className="text-5xl md:text-7xl lg:text-8xl font-extrabold tracking-tight mb-8 bg-clip-text text-transparent bg-gradient-to-b from-white via-white to-white/50">
                    Predict the Future of <br />
                    <span className="text-primary drop-shadow-[0_0_30px_rgba(253,242,253,0.3)]">Stock Market</span>
                </h1>
                
                <p className="text-lg md:text-xl text-white/60 max-w-2xl mb-12 leading-relaxed">
                    Harness the power of advanced machine learning to analyze market trends, predict stock movements, and make smarter investment decisions.
                </p>
                
                <div className="flex flex-col sm:flex-row items-center gap-4 w-full sm:w-auto">
                    <button 
                        onClick={onRegister}
                        className="w-full sm:w-auto px-8 py-4 text-base font-bold bg-primary text-black rounded-full hover:bg-opacity-90 transition-all shadow-[0_0_20px_rgba(253,242,253,0.3)] hover:shadow-[0_0_30px_rgba(253,242,253,0.5)] hover:scale-105"
                    >
                        Start for Free
                    </button>
                    <button 
                        onClick={onLogin}
                        className="w-full sm:w-auto px-8 py-4 text-base font-bold bg-white/5 text-white border border-white/10 rounded-full hover:bg-white/10 transition-all backdrop-blur-sm"
                    >
                        View Demo
                    </button>
                </div>

                {/* Abstract UI Preview */}
                <div className="relative w-full max-w-4xl mt-24 aspect-[16/9] rounded-xl bg-[#1E1E1E] border border-white/10 shadow-2xl overflow-hidden group">
                    <div className="absolute inset-0 bg-gradient-to-b from-transparent to-background-dark/80 z-10"></div>
                    
                    {/* Mock UI Elements */}
                    <div className="absolute top-0 left-0 right-0 h-12 bg-[#252025] border-b border-white/5 flex items-center px-4 gap-2">
                        <div className="w-3 h-3 rounded-full bg-red-500/20"></div>
                        <div className="w-3 h-3 rounded-full bg-yellow-500/20"></div>
                        <div className="w-3 h-3 rounded-full bg-green-500/20"></div>
                    </div>
                    
                    <div className="absolute top-20 left-8 right-8 bottom-8 flex gap-6">
                        <div className="w-64 hidden md:block h-full rounded-lg bg-white/5 border border-white/5 animate-pulse"></div>
                        <div className="flex-1 h-full rounded-lg bg-white/5 border border-white/5 flex flex-col p-6 gap-4">
                            <div className="w-1/3 h-8 rounded bg-white/10"></div>
                            <div className="flex-1 rounded bg-gradient-to-tr from-primary/5 to-transparent relative overflow-hidden">
                                <div className="absolute bottom-0 left-0 right-0 h-[60%] bg-gradient-to-t from-primary/10 to-transparent"></div>
                                {/* Chart Line */}
                                <svg className="absolute inset-0 w-full h-full" preserveAspectRatio="none">
                                    <path d="M0,100 C100,80 200,120 300,60 S500,80 600,40 L600,200 L0,200 Z" fill="url(#gradient)" opacity="0.2" />
                                    <path d="M0,100 C100,80 200,120 300,60 S500,80 600,40" fill="none" stroke="#FDF2FD" strokeWidth="3" />
                                    <defs>
                                        <linearGradient id="gradient" x1="0%" y1="0%" x2="0%" y2="100%">
                                            <stop offset="0%" stopColor="#FDF2FD" stopOpacity="1" />
                                            <stop offset="100%" stopColor="#FDF2FD" stopOpacity="0" />
                                        </linearGradient>
                                    </defs>
                                </svg>
                            </div>
                        </div>
                    </div>
                </div>
            </main>

            {/* Features Grid */}
            <section className="relative z-10 px-6 py-24 bg-black/20">
                <div className="max-w-7xl mx-auto grid grid-cols-1 md:grid-cols-3 gap-8">
                    {[
                        { title: "Real-time Analysis", desc: "Instant market data processing with millisecond latency.", icon: "bolt" },
                        { title: "AI Predictions", desc: "Advanced neural networks forecasting future trends.", icon: "psychology" },
                        { title: "Smart Portfolio", desc: "Automated balancing and risk management tools.", icon: "account_balance_wallet" }
                    ].map((feature, i) => (
                        <div key={i} className="p-8 rounded-2xl bg-white/5 border border-white/10 hover:bg-white/10 transition-colors backdrop-blur-sm">
                            <span className="material-symbols-outlined text-4xl text-primary mb-4">{feature.icon}</span>
                            <h3 className="text-xl font-bold text-white mb-2">{feature.title}</h3>
                            <p className="text-white/60">{feature.desc}</p>
                        </div>
                    ))}
                </div>
            </section>
        </div>
    );
};

export default LandingPage;

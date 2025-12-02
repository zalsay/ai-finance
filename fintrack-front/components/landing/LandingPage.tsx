import React from 'react';
import { useLanguage } from '../../contexts/LanguageContext';

interface LandingPageProps {
    onLogin: () => void;
    onRegister: () => void;
    onDemo: () => void;
}

const LandingPage: React.FC<LandingPageProps> = ({ onLogin, onRegister, onDemo }) => {
    const { t } = useLanguage();

    return (
        <div className="min-h-screen flex flex-col">
            {/* Navbar placeholder or simple header */}
            <header className="flex justify-between items-center p-6 border-b border-white/10">
                <div className="flex items-center gap-2">
                    <div className="w-8 h-8 bg-primary rounded-lg flex items-center justify-center">
                        <span className="material-symbols-outlined text-black text-xl">trending_up</span>
                    </div>
                    <span className="text-xl font-bold text-white tracking-tight">MeetlifeTimesForecast-V1.0</span>
                </div>
                <div className="flex gap-4">
                    <button 
                        onClick={onLogin}
                        className="text-white hover:text-primary transition-colors"
                    >
                        {t('login.loginButton')}
                    </button>
                    <button 
                        onClick={onRegister}
                        className="bg-primary text-black px-4 py-2 rounded-lg font-bold hover:opacity-90 transition-opacity"
                    >
                        {t('login.registerButton')}
                    </button>
                </div>
            </header>

            {/* Hero Section */}
            <main className="flex-1 flex items-center justify-center p-6">
                <div className="max-w-4xl w-full text-center space-y-8">
                    <h1 className="text-5xl md:text-7xl font-black text-white tracking-tighter leading-tight">
                        {t('login.title')}
                    </h1>
                    <p className="text-xl text-white/60 max-w-2xl mx-auto leading-relaxed">
                        {t('login.subtitle')}
                    </p>
                    
                    <div className="flex flex-col sm:flex-row gap-4 justify-center pt-8">
                        <button 
                            onClick={onRegister}
                            className="h-14 px-8 bg-primary text-black text-lg font-bold rounded-xl hover:opacity-90 transition-opacity flex items-center justify-center gap-2"
                        >
                            <span>Start for Free</span>
                            <span className="material-symbols-outlined">arrow_forward</span>
                        </button>
                        <button 
                            onClick={onDemo}
                            className="h-14 px-8 bg-white/5 text-white text-lg font-bold rounded-xl hover:bg-white/10 transition-colors border border-white/10"
                        >
                            View Demo
                        </button>
                    </div>

                    {/* Features Grid (Simplified) */}
                    <div className="grid grid-cols-1 md:grid-cols-3 gap-6 pt-20 text-left">
                        <div className="p-6 rounded-2xl bg-white/5 border border-white/10">
                            <span className="material-symbols-outlined text-primary text-3xl mb-4">auto_graph</span>
                            <h3 className="text-white text-lg font-bold mb-2">AI Predictions</h3>
                            <p className="text-white/60">Advanced machine learning algorithms forecasting stock movements.</p>
                        </div>
                        <div className="p-6 rounded-2xl bg-white/5 border border-white/10">
                            <span className="material-symbols-outlined text-primary text-3xl mb-4">monitoring</span>
                            <h3 className="text-white text-lg font-bold mb-2">Real-time Analysis</h3>
                            <p className="text-white/60">Live market data analysis to keep you ahead of the curve.</p>
                        </div>
                        <div className="p-6 rounded-2xl bg-white/5 border border-white/10">
                            <span className="material-symbols-outlined text-primary text-3xl mb-4">lock</span>
                            <h3 className="text-white text-lg font-bold mb-2">Secure Portfolio</h3>
                            <p className="text-white/60">Bank-grade security to protect your investment data.</p>
                        </div>
                    </div>
                </div>
            </main>

            <footer className="p-6 text-center text-white/40 text-sm">
                © 2024 FinTrack. All rights reserved.
            </footer>
        </div>
    );
};

export default LandingPage;

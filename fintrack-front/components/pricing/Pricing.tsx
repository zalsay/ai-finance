
import React from 'react';
import { useLanguage } from '../../contexts/LanguageContext';

const FeatureCard: React.FC<{ icon: string; title: string; description: string; }> = ({ icon, title, description }) => (
    <div className="flex flex-1 gap-4 rounded-xl border border-white/10 bg-white/5 p-6 flex-col">
        <span className="material-symbols-outlined text-primary text-3xl">{icon}</span>
        <div className="flex flex-col gap-1">
            <h3 className="text-white text-lg font-bold leading-tight">{title}</h3>
            <p className="text-white/60 text-sm font-normal leading-normal">{description}</p>
        </div>
    </div>
);

const TestimonialCard: React.FC<{ quote: string; name: string; image: string; rating: number; }> = ({ quote, name, image, rating }) => {
    const stars = Array.from({ length: 5 }, (_, i) => {
        if (i < Math.floor(rating)) return 'star';
        if (i < rating) return 'star_half';
        return 'star_outline';
    });

    return (
        <div className="rounded-xl border border-white/10 bg-white/5 p-8 flex flex-col justify-between h-full">
            <blockquote className="text-white/80 mb-6">"{quote}"</blockquote>
            <footer className="flex items-center gap-4">
                <img className="w-12 h-12 rounded-full object-cover" alt={`Profile picture of ${name}`} src={image}/>
                <div>
                    <p className="font-bold text-white">{name}</p>
                    <div className="flex text-primary">
                        {stars.map((starType, index) => (
                           <span key={index} className="material-symbols-outlined text-base">{starType}</span>
                        ))}
                    </div>
                </div>
            </footer>
        </div>
    );
};

const ComparisonRow: React.FC<{ feature: string; free: boolean | string; vip: boolean | string; }> = ({ feature, free, vip }) => (
    <tr className="border-t border-t-white/10">
        <td className="px-6 py-4">{feature}</td>
        <td className="px-6 py-4 text-center">
            {typeof free === 'boolean' ? (
                <span className={`material-symbols-outlined ${free ? 'text-primary' : 'text-white/40'}`}>{free ? 'done' : 'close'}</span>
            ) : ( free )}
        </td>
        <td className="px-6 py-4 text-center">
             {typeof vip === 'boolean' ? (
                <span className={`material-symbols-outlined ${vip ? 'text-primary' : 'text-white/40'}`}>{vip ? 'done' : 'close'}</span>
            ) : ( <span className="text-primary font-bold">{vip}</span> )}
        </td>
    </tr>
);


const Pricing: React.FC = () => {
    const { t } = useLanguage();
    return (
        <main className="flex flex-col gap-12 sm:gap-16 md:gap-24">
            <section className="mt-12 sm:mt-16 md:mt-20">
                <div className="text-center p-4">
                    <h1 className="text-white text-4xl font-black leading-tight tracking-tighter sm:text-6xl">{t('pricing.title')}</h1>
                    <h2 className="text-white/80 text-base sm:text-lg font-normal leading-normal max-w-3xl mx-auto mt-2">
                        {t('pricing.subtitle')}
                    </h2>
                    <button className="mt-8 flex mx-auto min-w-[84px] max-w-[480px] cursor-pointer items-center justify-center overflow-hidden rounded-lg h-12 px-6 bg-primary text-black text-base font-bold leading-normal tracking-[0.015em] hover:opacity-90 transition-opacity">
                        <span className="truncate">{t('pricing.upgradeNow')}</span>
                    </button>
                </div>
            </section>

            <section>
                <div className="flex flex-col gap-10 px-4 py-10">
                    <div className="flex flex-col gap-4 text-center">
                        <h2 className="text-white tracking-tight text-3xl font-bold leading-tight sm:text-4xl max-w-[720px] mx-auto">{t('pricing.vipBenefitsTitle')}</h2>
                        <p className="text-white/80 text-base font-normal leading-normal max-w-[720px] mx-auto">{t('pricing.vipBenefitsDesc')}</p>
                    </div>
                    <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-6">
                        <FeatureCard icon="clock_loader_40" title={t('pricing.feature1Title')} description={t('pricing.feature1Desc')} />
                        <FeatureCard icon="monitoring" title={t('pricing.feature2Title')} description={t('pricing.feature2Desc')} />
                        <FeatureCard icon="insights" title={t('pricing.feature3Title')} description={t('pricing.feature3Desc')} />
                        <FeatureCard icon="view_list" title={t('pricing.feature4Title')} description={t('pricing.feature4Desc')} />
                        <FeatureCard icon="groups" title={t('pricing.feature5Title')} description={t('pricing.feature5Desc')} />
                        <FeatureCard icon="visibility_off" title={t('pricing.feature6Title')} description={t('pricing.feature6Desc')} />
                    </div>
                </div>
            </section>
            
            <section>
                <h2 className="text-white text-3xl font-bold leading-tight tracking-tight px-4 pb-6 pt-5 text-center">{t('pricing.comparePlans')}</h2>
                <div className="px-4 py-3">
                    <div className="flex overflow-hidden rounded-xl border border-white/10 bg-white/[.02]">
                        <table className="w-full">
                            <thead>
                                <tr className="bg-white/5">
                                    <th className="px-6 py-4 text-left text-white font-semibold w-1/2 sm:w-2/3">{t('pricing.feature')}</th>
                                    <th className="px-6 py-4 text-center text-white font-semibold">{t('pricing.free')}</th>
                                    <th className="px-6 py-4 text-center text-white font-semibold">{t('pricing.vip')}</th>
                                </tr>
                            </thead>
                            <tbody className="text-white/80">
                                <ComparisonRow feature={t('pricing.dataRefreshRate')} free={t('pricing.standard')} vip={t('pricing.realtime')} />
                                <ComparisonRow feature={t('pricing.watchlistNumber')} free="3" vip={t('pricing.unlimited')} />
                                <ComparisonRow feature={t('pricing.advancedAnalytics')} free={false} vip={true} />
                                <ComparisonRow feature={t('pricing.aiInsights')} free={false} vip={true} />
                                <ComparisonRow feature={t('pricing.communityAccess')} free={false} vip={true} />
                                <ComparisonRow feature={t('pricing.adFree')} free={false} vip={true} />
                            </tbody>
                        </table>
                    </div>
                </div>
            </section>

            <section className="px-4 py-10">
                <h2 className="text-white text-3xl font-bold leading-tight tracking-tight text-center mb-10">{t('pricing.testimonialTitle')}</h2>
                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-8">
                    <TestimonialCard name="Sarah J." quote="The real-time data is a game-changer. I've made smarter decisions in the last month than I did all of last year. Absolutely worth it." image="https://picsum.photos/seed/sarah/48/48" rating={5} />
                    <TestimonialCard name="Michael B." quote="The AI insights found an opportunity I would have completely missed. It's like having a personal analyst working for me 24/7." image="https://picsum.photos/seed/michael/48/48" rating={5} />
                    <TestimonialCard name="Emily K." quote="Finally, an ad-free experience. I can focus on the charts without any distractions. The clean interface makes all the difference." image="https://picsum.photos/seed/emily/48/48" rating={4.5} />
                </div>
            </section>

            <section className="px-4 py-16">
                <div className="max-w-md mx-auto rounded-2xl border border-primary/50 bg-white/5 p-8 text-center shadow-2xl shadow-primary/10">
                    <h2 className="text-primary text-lg font-bold">{t('pricing.vipMembership')}</h2>
                    <p className="text-5xl font-black text-white mt-2">$19<span className="text-lg font-medium text-white/60"> / {t('pricing.month')}</span></p>
                    <p className="text-white/60 mt-2">{t('pricing.billingInfo')}</p>
                    <ul className="text-left text-white/80 space-y-3 mt-8">
                        <li className="flex items-center gap-3"><span className="material-symbols-outlined text-primary">done</span>{t('pricing.allFeatures')}</li>
                        <li className="flex items-center gap-3"><span className="material-symbols-outlined text-primary">done</span>{t('pricing.prioritySupport')}</li>
                        <li className="flex items-center gap-3"><span className="material-symbols-outlined text-primary">done</span>{t('pricing.betaAccess')}</li>
                    </ul>
                    <button className="w-full mt-10 flex min-w-[84px] cursor-pointer items-center justify-center overflow-hidden rounded-lg h-12 px-6 bg-primary text-black text-base font-bold leading-normal tracking-[0.015em] hover:opacity-90 transition-opacity">
                        <span className="truncate">{t('pricing.upgradeToVip')}</span>
                    </button>
                    <div className="flex items-center justify-center gap-2 mt-4 text-xs text-white/50">
                        <span className="material-symbols-outlined text-sm">lock</span>
                        <span>{t('pricing.securePayment')}</span>
                    </div>
                </div>
            </section>
        </main>
    );
};

export default Pricing;

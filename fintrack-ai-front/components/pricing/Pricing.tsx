
import React from 'react';

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
    return (
        <main className="flex flex-col gap-12 sm:gap-16 md:gap-24">
            <section className="mt-12 sm:mt-16 md:mt-20">
                <div className="text-center p-4">
                    <h1 className="text-white text-4xl font-black leading-tight tracking-tighter sm:text-6xl">Unlock Your Full Trading Potential.</h1>
                    <h2 className="text-white/80 text-base sm:text-lg font-normal leading-normal max-w-3xl mx-auto mt-2">
                        Gain exclusive access to advanced analytics, real-time data, and pro-level tools with a VIP membership.
                    </h2>
                    <button className="mt-8 flex mx-auto min-w-[84px] max-w-[480px] cursor-pointer items-center justify-center overflow-hidden rounded-lg h-12 px-6 bg-primary text-black text-base font-bold leading-normal tracking-[0.015em] hover:opacity-90 transition-opacity">
                        <span className="truncate">Upgrade to VIP Now</span>
                    </button>
                </div>
            </section>

            <section>
                <div className="flex flex-col gap-10 px-4 py-10">
                    <div className="flex flex-col gap-4 text-center">
                        <h2 className="text-white tracking-tight text-3xl font-bold leading-tight sm:text-4xl max-w-[720px] mx-auto">Upgrade for Exclusive VIP Benefits</h2>
                        <p className="text-white/80 text-base font-normal leading-normal max-w-[720px] mx-auto">Enhance your investment strategy with powerful tools and real-time insights designed for serious investors.</p>
                    </div>
                    <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-6">
                        <FeatureCard icon="clock_loader_40" title="Real-Time Market Data" description="Stay ahead of the market with instant data updates, no delays." />
                        <FeatureCard icon="monitoring" title="Advanced Charting Tools" description="Utilize professional-grade tools for in-depth technical analysis." />
                        <FeatureCard icon="insights" title="AI-Powered Insights" description="Leverage our AI to analyze your portfolio and uncover new opportunities." />
                        <FeatureCard icon="view_list" title="Unlimited Watchlists" description="Track all the stocks you're interested in with no limits." />
                        <FeatureCard icon="groups" title="Exclusive Community" description="Join a private community of expert traders to share strategies." />
                        <FeatureCard icon="visibility_off" title="Ad-Free Experience" description="Focus on your investments with a clean, distraction-free interface." />
                    </div>
                </div>
            </section>
            
            <section>
                <h2 className="text-white text-3xl font-bold leading-tight tracking-tight px-4 pb-6 pt-5 text-center">Compare Our Plans</h2>
                <div className="px-4 py-3">
                    <div className="flex overflow-hidden rounded-xl border border-white/10 bg-white/[.02]">
                        <table className="w-full">
                            <thead>
                                <tr className="bg-white/5">
                                    <th className="px-6 py-4 text-left text-white font-semibold w-1/2 sm:w-2/3">Feature</th>
                                    <th className="px-6 py-4 text-center text-white font-semibold">Free</th>
                                    <th className="px-6 py-4 text-center text-white font-semibold">VIP</th>
                                </tr>
                            </thead>
                            <tbody className="text-white/80">
                                <ComparisonRow feature="Data Refresh Rate" free="Standard" vip="Real-time" />
                                <ComparisonRow feature="Number of Watchlists" free="3" vip="Unlimited" />
                                <ComparisonRow feature="Advanced Analytics" free={false} vip={true} />
                                <ComparisonRow feature="AI Portfolio Insights" free={false} vip={true} />
                                <ComparisonRow feature="Exclusive Community Access" free={false} vip={true} />
                                <ComparisonRow feature="Ad-Free Experience" free={false} vip={true} />
                            </tbody>
                        </table>
                    </div>
                </div>
            </section>

            <section className="px-4 py-10">
                <h2 className="text-white text-3xl font-bold leading-tight tracking-tight text-center mb-10">What Our VIP Members Are Saying</h2>
                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-8">
                    <TestimonialCard name="Sarah J." quote="The real-time data is a game-changer. I've made smarter decisions in the last month than I did all of last year. Absolutely worth it." image="https://picsum.photos/seed/sarah/48/48" rating={5} />
                    <TestimonialCard name="Michael B." quote="The AI insights found an opportunity I would have completely missed. It's like having a personal analyst working for me 24/7." image="https://picsum.photos/seed/michael/48/48" rating={5} />
                    <TestimonialCard name="Emily K." quote="Finally, an ad-free experience. I can focus on the charts without any distractions. The clean interface makes all the difference." image="https://picsum.photos/seed/emily/48/48" rating={4.5} />
                </div>
            </section>

            <section className="px-4 py-16">
                <div className="max-w-md mx-auto rounded-2xl border border-primary/50 bg-white/5 p-8 text-center shadow-2xl shadow-primary/10">
                    <h2 className="text-primary text-lg font-bold">VIP Membership</h2>
                    <p className="text-5xl font-black text-white mt-2">$19<span className="text-lg font-medium text-white/60"> / mo</span></p>
                    <p className="text-white/60 mt-2">Billed monthly, cancel anytime.</p>
                    <ul className="text-left text-white/80 space-y-3 mt-8">
                        <li className="flex items-center gap-3"><span className="material-symbols-outlined text-primary">done</span>All VIP features included</li>
                        <li className="flex items-center gap-3"><span className="material-symbols-outlined text-primary">done</span>Priority customer support</li>
                        <li className="flex items-center gap-3"><span className="material-symbols-outlined text-primary">done</span>Early access to beta features</li>
                    </ul>
                    <button className="w-full mt-10 flex min-w-[84px] cursor-pointer items-center justify-center overflow-hidden rounded-lg h-12 px-6 bg-primary text-black text-base font-bold leading-normal tracking-[0.015em] hover:opacity-90 transition-opacity">
                        <span className="truncate">Upgrade to VIP</span>
                    </button>
                    <div className="flex items-center justify-center gap-2 mt-4 text-xs text-white/50">
                        <span className="material-symbols-outlined text-sm">lock</span>
                        <span>Secure 256-bit SSL encrypted payment</span>
                    </div>
                </div>
            </section>
        </main>
    );
};

export default Pricing;

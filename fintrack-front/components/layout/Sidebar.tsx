
import React, { useState, useEffect } from 'react';
import { View } from '../../types';
import { NAVIGATION_ITEMS } from '../../constants';
import { useLanguage } from '../../contexts/LanguageContext';
import LanguageSwitcher from './LanguageSwitcher';
import { authAPI } from '../../services/apiService';

interface SidebarProps {
  currentView: View;
  setCurrentView: (view: View) => void;
  onLogout: () => void;
  isDemoMode?: boolean;
}

const Sidebar: React.FC<SidebarProps> = ({ currentView, setCurrentView, onLogout, isDemoMode = false }) => {
    const { t } = useLanguage();
    const [userEmail, setUserEmail] = useState<string>('');
    const [membershipLevel, setMembershipLevel] = useState<number>(0);

    useEffect(() => {
        if (isDemoMode) {
            setUserEmail('Demo User');
            return;
        }
        
        const fetchProfile = async () => {
            try {
                const user = await authAPI.getProfile();
                setUserEmail(user.email);
                setMembershipLevel(user.membership_level ?? 0);
            } catch (error) {
                console.error('Failed to fetch user profile', error);
            }
        };
        fetchProfile();
    }, [isDemoMode]);
    
    return (
        <aside className="w-64 shrink-0 bg-background-dark p-4 flex-col justify-between hidden lg:flex">
            <div className="flex flex-col gap-8">
                <div className="flex items-center gap-2 px-2">
                    <span className="material-symbols-outlined text-primary text-3xl">trending_up</span>
                    <h1 className="text-white text-xl font-bold">{t('sidebar.title')}</h1>
                </div>
                    <div className="flex flex-col gap-4">
                        <div className="flex gap-3 px-2">
                            <div className="flex flex-col">
                                <h2 className="text-white text-base font-medium leading-normal">{t('sidebar.hello')}</h2>
                                <p className="text-white/60 text-sm font-normal leading-normal">{userEmail || t('sidebar.loading')}</p>
                                <div className="mt-1">
                                    <span className="px-2 py-0.5 rounded text-[10px] font-bold"
                                          style={{ backgroundColor: 'rgba(255,255,255,0.08)', border: '1px solid rgba(255,255,255,0.1)' }}>
                                        {(() => {
                                            switch (membershipLevel) {
                                                case 3: return 'UVIP';
                                                case 2: return 'SVIP';
                                                case 1: return 'VIP';
                                                default: return '普通会员';
                                            }
                                        })()}
                                    </span>
                                </div>
                            </div>
                        </div>
                    
                    {/* Language Switcher */}
                    <div className="px-2">
                        <LanguageSwitcher />
                    </div>
                    
                    <nav className="flex flex-col gap-2">
                        {NAVIGATION_ITEMS.map(item => (
                            <a
                                key={item.id}
                                className={`flex items-center gap-3 px-3 py-2 rounded-lg transition-colors cursor-pointer ${
                                    currentView === item.id 
                                    ? 'bg-primary/20 text-primary' 
                                    : 'text-white/80 hover:bg-white/10 hover:text-white'
                                }`}
                                onClick={() => setCurrentView(item.id)}
                            >
                                <span className="material-symbols-outlined" style={{ fontVariationSettings: currentView === item.id ? "'FILL' 1" : "" }}>
                                    {item.icon}
                                </span>
                                <p className="text-sm font-medium leading-normal">{t(`nav.${item.id}`)}</p>
                            </a>
                        ))}
                    </nav>
                </div>
            </div>
            <div className="flex flex-col gap-1">
                <a className="flex items-center gap-3 px-3 py-2 rounded-lg transition-colors cursor-pointer text-white/80 hover:bg-white/10 hover:text-white">
                    <span className="material-symbols-outlined">settings</span>
                    <p className="text-white text-sm font-medium leading-normal">{t('common.settings') || 'Settings'}</p>
                </a>
                <a onClick={onLogout} className="flex items-center gap-3 px-3 py-2 rounded-lg transition-colors cursor-pointer text-white/80 hover:bg-white/10 hover:text-white">
                    <span className="material-symbols-outlined">logout</span>
                    <p className="text-white text-sm font-medium leading-normal">{t('common.logout') || 'Logout'}</p>
                </a>
            </div>
        </aside>
    );
};

export default Sidebar;

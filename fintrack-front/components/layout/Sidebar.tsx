
import React from 'react';
import { View } from '../../types';
import { NAVIGATION_ITEMS } from '../../constants';
import { useLanguage } from '../../contexts/LanguageContext';
import LanguageSwitcher from './LanguageSwitcher';

interface SidebarProps {
  currentView: View;
  setCurrentView: (view: View) => void;
  onLogout: () => void;
}

const Sidebar: React.FC<SidebarProps> = ({ currentView, setCurrentView, onLogout }) => {
    const { t } = useLanguage();
    
    return (
        <aside className="w-64 shrink-0 bg-background-dark p-4 flex-col justify-between hidden lg:flex">
            <div className="flex flex-col gap-8">
                <div className="flex items-center gap-2 px-2">
                    <span className="material-symbols-outlined text-primary text-3xl">trending_up</span>
                    <h1 className="text-white text-xl font-bold">FinTrack AI</h1>
                </div>
                <div className="flex flex-col gap-4">
                    <div className="flex gap-3 px-2">
                        <img className="size-10 rounded-full object-cover" src="https://picsum.photos/seed/user/40/40" alt="User avatar" />
                        <div className="flex flex-col">
                            <h2 className="text-white text-base font-medium leading-normal">Alex Doe</h2>
                            <p className="text-white/60 text-sm font-normal leading-normal">alex.doe@email.com</p>
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

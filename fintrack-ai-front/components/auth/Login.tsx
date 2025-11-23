
import React, { useState, useEffect } from 'react';
import LogoIcon from '../icons/LogoIcon';
import GoogleIcon from '../icons/GoogleIcon';
import { useLanguage } from '../../contexts/LanguageContext';
import { authAPI } from '../../services/apiService';

interface LoginProps {
    onLogin: () => void;
}

type FormType = 'login' | 'register';

// 将InputField组件移到外部以避免重新渲染时重新创建
const InputField: React.FC<{
    id: string;
    label: string;
    type: string;
    placeholder: string;
    value: string;
    onChange: (value: string) => void;
    required?: boolean;
    disabled?: boolean;
}> = ({ id, label, type, placeholder, value, onChange, required = true, disabled = false }) => (
    <div className="flex flex-col">
        <label className="text-[#E0E0E0] text-sm font-medium leading-normal pb-2" htmlFor={id}>{label}</label>
        <input
            className="form-input flex w-full min-w-0 flex-1 resize-none overflow-hidden rounded-lg text-white focus:outline-0 focus:ring-2 focus:ring-primary/50 border border-[#444] bg-[#2a2a2a] h-12 placeholder:text-[#757575] p-3 text-base font-normal leading-normal"
            id={id}
            placeholder={placeholder}
            type={type}
            value={value}
            onChange={(e) => onChange(e.target.value)}
            required={required}
            disabled={disabled}
            autoComplete={type === 'password' ? 'current-password' : type === 'email' ? 'email' : 'off'}
        />
    </div>
);

// 将CheckboxField组件移到外部以避免重新渲染时重新创建
const CheckboxField: React.FC<{
    id: string;
    label: string;
    checked: boolean;
    onChange: (checked: boolean) => void;
    disabled?: boolean;
}> = ({ id, label, checked, onChange, disabled = false }) => (
    <div className="flex items-center gap-3">
        <input
            type="checkbox"
            id={id}
            checked={checked}
            onChange={(e) => onChange(e.target.checked)}
            className="w-4 h-4 text-primary bg-[#2a2a2a] border-[#444] rounded focus:ring-primary/50 focus:ring-2"
            disabled={disabled}
        />
        <label htmlFor={id} className="text-[#E0E0E0] text-sm font-medium leading-normal cursor-pointer">
            {label}
        </label>
    </div>
);

const Login: React.FC<LoginProps> = ({ onLogin }) => {
    const [formType, setFormType] = useState<FormType>('login');
    const [email, setEmail] = useState('');
    const [password, setPassword] = useState('');
    const [username, setUsername] = useState('');
    const [rememberPassword, setRememberPassword] = useState(false);
    const [isLoading, setIsLoading] = useState(false);
    const [error, setError] = useState<string | null>(null);
    const { t } = useLanguage();

    // 组件加载时检查是否有保存的邮箱
    useEffect(() => {
        const savedEmail = localStorage.getItem('rememberedEmail');
        const shouldRemember = localStorage.getItem('rememberPassword') === 'true';

        if (savedEmail && shouldRemember) {
            setEmail(savedEmail);
            setRememberPassword(true);
        }
    }, []);

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault();
        setIsLoading(true);
        setError(null);

        try {
            if (formType === 'login') {
                const response = await authAPI.login(email, password);
                // 如果用户选择保存密码，将凭据保存到localStorage
                if (rememberPassword) {
                    localStorage.setItem('rememberedEmail', email);
                    localStorage.setItem('rememberPassword', 'true');
                } else {
                    localStorage.removeItem('rememberedEmail');
                    localStorage.removeItem('rememberPassword');
                }
            } else {
                await authAPI.register(email, username, password);
                // Force reload after registration to pick up auth state
                // Small delay to ensure localStorage write completes
                await new Promise(resolve => setTimeout(resolve, 100));
                window.location.reload();
                return; // Prevent onLogin() from being called
            }
            // Force reload after login to pick up auth state
            // Small delay to ensure localStorage write completes
            await new Promise(resolve => setTimeout(resolve, 100));
            window.location.reload();
        } catch (err: any) {
            setError(err.message);
        } finally {
            setIsLoading(false);
        }
    };

    const TabButton: React.FC<{ type: FormType; label: string }> = ({ type, label }) => (
        <button
            onClick={(e) => { e.preventDefault(); setFormType(type); setError(null); }}
            className={`flex flex-col flex-1 items-center justify-center border-b-[3px] pb-[13px] pt-4 ${formType === type ? 'border-b-primary text-white' : 'border-b-transparent text-[#9E9E9E]'}`}
        >
            <p className="text-sm font-bold leading-normal tracking-[0.015em]">{label}</p>
        </button>
    );

    return (
        <div className="relative flex min-h-screen w-full flex-col items-center justify-center bg-container-dark text-[#E0E0E0] p-4 sm:p-6 lg:p-8">
            <div className="w-full max-w-4xl overflow-hidden rounded-xl bg-[#1E1E1E] shadow-2xl flex flex-col md:flex-row">
                <div className="w-full md:w-1/2 bg-background-dark p-8 sm:p-12 flex flex-col justify-center">
                    <div className="flex items-center gap-4 text-white mb-8">
                        <LogoIcon className="size-8" />
                        <h2 className="text-white text-2xl font-bold leading-tight tracking-[-0.015em]">FinTrack AI</h2>
                    </div>
                    <h1 className="text-white tracking-tight text-4xl font-bold leading-tight mb-4">{t('login.title')}</h1>
                    <p className="text-[#91caae] text-base font-normal leading-normal">
                        {t('login.subtitle')}
                    </p>
                </div>

                <div className="w-full md:w-1/2 p-8 sm:p-12 flex flex-col bg-[#1E1E1E]">
                    <div className="w-full">
                        <div className="flex border-b border-[#333]">
                            <TabButton type="login" label={t('login.loginTab')} />
                            <TabButton type="register" label={t('login.registerTab')} />
                        </div>
                    </div>

                    <div className="flex flex-col flex-1 mt-8">
                        <h3 className="text-white text-2xl font-bold leading-tight mb-6">
                            {formType === 'login' ? t('login.welcomeBack') : t('login.createAccount')}
                        </h3>

                        {error && (
                            <div className="mb-4 p-3 bg-red-500/10 border border-red-500/20 rounded-lg">
                                <p className="text-red-400 text-sm">{error}</p>
                            </div>
                        )}

                        <form className="flex flex-col gap-5" onSubmit={handleSubmit}>
                            {formType === 'register' && (
                                <InputField
                                    id="fullname"
                                    label={t('login.fullName')}
                                    type="text"
                                    placeholder={t('login.fullNamePlaceholder')}
                                    value={username}
                                    onChange={setUsername}
                                    disabled={isLoading}
                                />
                            )}
                            <InputField
                                id="email"
                                label={t('login.emailAddress')}
                                type="email"
                                placeholder={t('login.emailPlaceholder')}
                                value={email}
                                onChange={setEmail}
                                disabled={isLoading}
                            />
                            <InputField
                                id="password"
                                label={t('login.password')}
                                type="password"
                                placeholder={t('login.passwordPlaceholder')}
                                value={password}
                                onChange={setPassword}
                                disabled={isLoading}
                            />

                            {formType === 'login' && (
                                <div className="flex items-center justify-between -mt-2">
                                    <CheckboxField
                                        id="rememberPassword"
                                        label="保存密码"
                                        checked={rememberPassword}
                                        onChange={setRememberPassword}
                                        disabled={isLoading}
                                    />
                                    <a className="text-sm text-primary hover:underline" href="#">{t('login.forgotPassword')}</a>
                                </div>
                            )}

                            {formType === 'register' && <div className="-mt-2"></div>}

                            <button
                                className="flex items-center justify-center whitespace-nowrap rounded-lg text-sm font-bold h-12 px-6 bg-primary text-black mt-4 hover:bg-opacity-90 transition-colors focus:outline-none focus:ring-2 focus:ring-primary/50 focus:ring-offset-2 focus:ring-offset-[#1E1E1E] disabled:opacity-50 disabled:cursor-not-allowed"
                                type="submit"
                                disabled={isLoading}
                            >
                                {isLoading ? (
                                    <div className="flex items-center gap-2">
                                        <div className="w-4 h-4 border-2 border-black border-t-transparent rounded-full animate-spin"></div>
                                        {formType === 'login' ? '登录中...' : '注册中...'}
                                    </div>
                                ) : (
                                    formType === 'login' ? t('login.signIn') : t('login.register')
                                )}
                            </button>

                            <div className="relative flex items-center py-2">
                                <div className="flex-grow border-t border-[#444]"></div>
                                <span className="flex-shrink mx-4 text-xs text-[#9E9E9E]">{t('login.or')}</span>
                                <div className="flex-grow border-t border-[#444]"></div>
                            </div>

                            <button className="flex items-center justify-center whitespace-nowrap rounded-lg text-sm font-medium h-12 px-6 bg-[#2a2a2a] text-white border border-[#444] hover:bg-[#333] transition-colors focus:outline-none focus:ring-2 focus:ring-primary/50 focus:ring-offset-2 focus:ring-offset-[#1E1E1E] gap-2 disabled:opacity-50 disabled:cursor-not-allowed" type="button" onClick={onLogin} disabled={isLoading}>
                                <GoogleIcon className="h-5 w-5" />
                                {t('login.continueWithGoogle')}
                            </button>
                        </form>
                    </div>
                </div>
            </div>
        </div>
    );
};

export default Login;

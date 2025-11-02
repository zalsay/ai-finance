
import React, { useState } from 'react';
import LogoIcon from '../icons/LogoIcon';
import GoogleIcon from '../icons/GoogleIcon';

interface LoginProps {
    onLogin: () => void;
}

type FormType = 'login' | 'register';

const Login: React.FC<LoginProps> = ({ onLogin }) => {
    const [formType, setFormType] = useState<FormType>('login');

    const TabButton: React.FC<{ type: FormType; label: string }> = ({ type, label }) => (
        <button
            onClick={(e) => { e.preventDefault(); setFormType(type); }}
            className={`flex flex-col flex-1 items-center justify-center border-b-[3px] pb-[13px] pt-4 ${formType === type ? 'border-b-primary text-white' : 'border-b-transparent text-[#9E9E9E]'}`}
        >
            <p className="text-sm font-bold leading-normal tracking-[0.015em]">{label}</p>
        </button>
    );

    const InputField: React.FC<{ id: string; label: string; type: string; placeholder: string; }> = ({ id, label, type, placeholder }) => (
         <div className="flex flex-col">
            <label className="text-[#E0E0E0] text-sm font-medium leading-normal pb-2" htmlFor={id}>{label}</label>
            <input
                className="form-input flex w-full min-w-0 flex-1 resize-none overflow-hidden rounded-lg text-white focus:outline-0 focus:ring-2 focus:ring-primary/50 border border-[#444] bg-[#2a2a2a] h-12 placeholder:text-[#757575] p-3 text-base font-normal leading-normal"
                id={id}
                placeholder={placeholder}
                type={type}
            />
        </div>
    );

    return (
        <div className="relative flex min-h-screen w-full flex-col items-center justify-center bg-container-dark text-[#E0E0E0] p-4 sm:p-6 lg:p-8">
            <div className="w-full max-w-4xl overflow-hidden rounded-xl bg-[#1E1E1E] shadow-2xl flex flex-col md:flex-row">
                <div className="w-full md:w-1/2 bg-background-dark p-8 sm:p-12 flex flex-col justify-center">
                    <div className="flex items-center gap-4 text-white mb-8">
                        <LogoIcon className="size-8" />
                        <h2 className="text-white text-2xl font-bold leading-tight tracking-[-0.015em]">FinTrack AI</h2>
                    </div>
                    <h1 className="text-white tracking-tight text-4xl font-bold leading-tight mb-4">Your Portfolio, Perfected.</h1>
                    <p className="text-[#91caae] text-base font-normal leading-normal">
                        Track your stocks with AI-powered predictions and unparalleled insight. Make smarter investment decisions today.
                    </p>
                </div>
                
                <div className="w-full md:w-1/2 p-8 sm:p-12 flex flex-col bg-[#1E1E1E]">
                    <div className="w-full">
                        <div className="flex border-b border-[#333]">
                           <TabButton type="login" label="Login" />
                           <TabButton type="register" label="Register" />
                        </div>
                    </div>
                    
                    <div className="flex flex-col flex-1 mt-8">
                        <h3 className="text-white text-2xl font-bold leading-tight mb-6">
                            {formType === 'login' ? 'Welcome Back' : 'Create an Account'}
                        </h3>
                        <form className="flex flex-col gap-5" onSubmit={(e) => { e.preventDefault(); onLogin(); }}>
                            {formType === 'register' && <InputField id="fullname" label="Full Name" type="text" placeholder="Enter your full name" />}
                            <InputField id="email" label="Email Address" type="email" placeholder="Enter your email" />
                            <InputField id="password" label="Password" type="password" placeholder="Enter your password" />
                            
                            {formType === 'login' && <a className="text-sm text-primary hover:underline text-right -mt-2" href="#">Forgot Password?</a>}
                            
                            <button className="flex items-center justify-center whitespace-nowrap rounded-lg text-sm font-bold h-12 px-6 bg-primary text-black mt-4 hover:bg-opacity-90 transition-colors focus:outline-none focus:ring-2 focus:ring-primary/50 focus:ring-offset-2 focus:ring-offset-[#1E1E1E]" type="submit">
                                {formType === 'login' ? 'Login' : 'Register'}
                            </button>

                            <div className="relative flex items-center py-2">
                                <div className="flex-grow border-t border-[#444]"></div>
                                <span className="flex-shrink mx-4 text-xs text-[#9E9E9E]">OR</span>
                                <div className="flex-grow border-t border-[#444]"></div>
                            </div>
                            
                            <button className="flex items-center justify-center whitespace-nowrap rounded-lg text-sm font-medium h-12 px-6 bg-[#2a2a2a] text-white border border-[#444] hover:bg-[#333] transition-colors focus:outline-none focus:ring-2 focus:ring-primary/50 focus:ring-offset-2 focus:ring-offset-[#1E1E1E] gap-2" type="button" onClick={onLogin}>
                                <GoogleIcon className="h-5 w-5" />
                                Continue with Google
                            </button>
                        </form>
                    </div>
                </div>
            </div>
        </div>
    );
};

export default Login;

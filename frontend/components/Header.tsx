'use client';
import { useEffect, useState } from 'react';

export default function Header() {
    const [showBorder, setShowBorder] = useState(false);

    useEffect(() => {
        function handleScroll() {
            if (window.scrollY > 25) {
                setShowBorder(true);
            } else {
                setShowBorder(false);
            }
        }

        window.addEventListener('scroll', handleScroll);

        return () => {
            window.removeEventListener('scroll', handleScroll);
        };
    }, []);

    return (
        <header className="sticky top-0 z-50">
            <div
                className={
                    `px-6 py-3 backdrop-blur-sm  bg-opacity-60 transition-all duration-700 border-b` +
                    (showBorder
                        ? ' border-neutral-200 bg-white'
                        : ' border-transparent')
                }
            >
                <div className="flex flex-row justify-between">
                    <a
                        href="/"
                        className="font-normal text-sm justify-center items-center flex"
                    >
                        Domain Generator
                    </a>
                    <div className="flex flex-row font-normal text-sm gap-2 tracking-tight">
                        <a
                            href="/login"
                            className="bg-black text-white px-3 py-[2px] rounded-[5px] border border-black flex items-center"
                        >
                            Login
                        </a>
                        {/*                         <a
                            href="/"
                            className="bg-white text-black px-3 py-[2px] rounded-[5px] border border-black flex items-center"
                        >
                            Signup
                        </a> */}
                    </div>
                </div>
            </div>
        </header>
    );
}

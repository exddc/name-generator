'use client';

// Libraries
import { useState } from 'react';
import { cn } from '@/lib/utils';

// Components
import { DomainGenerator } from '@/components/DomainGenerator';

export default function Hero() {
    const [hasDomains, setHasDomains] = useState(false);

    return (
        <div
            id="hero-domain-generator"
            className={cn(
                'w-full flex flex-col items-center justify-center transition-all duration-500',
                hasDomains ? '-mt-64' : '-mt-32'
            )}
        >
            <div
                id="hero-content"
                className={cn(
                    'w-full max-w-3xl flex flex-col gap-2 items-center transition-all duration-1000 z-10 text-center'
                )}
            >
                <h1 className="text-5xl font-bold flex flex-col tracking-tighter">
                    <span>Generate domain names</span>
                    <span>that are guaranteed available</span>
                </h1>
                <p className=" font-light text-balance text-lg tracking-tight">
                    Skip the guesswork and go straight to securing a name that
                    fits your brand and vision
                </p>
            </div>
            <DomainGenerator onDomainsStatusChange={setHasDomains} />
        </div>
    );
}

'use client';

import React, { useState } from 'react';
import { motion } from 'motion/react';
import { Button } from '@/components/ui/button';
import { Textarea } from '@/components/ui/textarea';
import { FlipWords } from '@/components/ui/flip-words';

interface DomainData {
    domain: string;
    status: string;
}

export default function Home() {
    const [userInput, setUserInput] = useState('');
    const [domains, setDomains] = useState<DomainData[]>([]);
    const [errorMsg, setErrorMsg] = useState<string | null>(null);
    const [isLoading, setIsLoading] = useState(false);

    const flipwords = ['app', 'service', 'company', 'idea', 'project'];

    const handleSuggestStream = (e: React.FormEvent) => {
        e.preventDefault();
        setIsLoading(true);
        setDomains([]);
        setErrorMsg(null);

        const url = `http://0.0.0.0:8000/v1/suggest_stream?query=${encodeURIComponent(
            userInput
        )}`;

        const evtSource = new EventSource(url);

        evtSource.onopen = () => {
            console.log('SSE connection opened.');
        };

        evtSource.onerror = (err) => {
            console.error('SSE onerror triggered:', err);
            setErrorMsg(
                'A network or server error occurred while streaming data.'
            );
            setIsLoading(false);
            evtSource.close();
        };

        evtSource.onmessage = (e) => {
            console.log('Generic message:', e.data);
        };

        evtSource.addEventListener('domain_suggestion', (e: MessageEvent) => {
            try {
                const dataObj = JSON.parse(e.data) as DomainData;
                setDomains((prev) => [...prev, dataObj]);
            } catch (parseErr) {
                console.error(
                    'Error parsing domain_suggestion data:',
                    parseErr
                );
            }
        });

        evtSource.addEventListener('error', (e: any) => {
            console.error('SSE error event:', e.data);
            setErrorMsg(e.data ?? 'Unknown error occurred.');
        });

        evtSource.addEventListener('done', (e: MessageEvent) => {
            console.log('SSE done event:', e.data);
            setIsLoading(false);
            evtSource.close();
        });
    };

    const freeDomains = domains.filter((d) => d.status === 'free');
    const registeredDomains = domains.filter((d) => d.status === 'registered');
    const unknownDomains = domains.filter(
        (d) => d.status !== 'free' && d.status !== 'registered'
    );

    const hasAnyDomains =
        freeDomains.length > 0 ||
        registeredDomains.length > 0 ||
        unknownDomains.length > 0;

    function renderDomainRow(item: DomainData, index: number) {
        return (
            <li
                key={index}
                className="flex border border-[#D9D9D9] px-4 py-2 rounded-xl text-sm justify-between bg-white"
            >
                <a
                    href={'https://' + item.domain}
                    target="_blank"
                    rel="noreferrer"
                >
                    {item.domain}
                </a>
                <div className="flex gap-4 items-center">
                    <p
                        className={
                            (item.status === 'free'
                                ? 'bg-green-300 border-green-800'
                                : item.status === 'registered'
                                ? 'bg-red-300 border-red-800'
                                : 'bg-yellow-200 border-yellow-800') +
                            ' text-black font-semibold text-xs border px-2 flex items-center h-fit rounded-xl'
                        }
                    >
                        {item.status === 'free'
                            ? 'Available'
                            : item.status === 'registered'
                            ? 'Registered'
                            : 'Unknown'}
                    </p>
                    <button
                        className="pl-4 pr-2 border-l border-[#D9D9D9] bg-white"
                        disabled={isLoading}
                    >
                        Generate similar
                    </button>
                </div>
            </li>
        );
    }

    return (
        <main className="flex flex-col items-center justify-center pt-40">
            <div
                className={
                    'transition-all duration-1000 flex' +
                    (hasAnyDomains
                        ? ' h-[350px] blur-[180px]'
                        : ' h-[150px] blur-[120px]')
                }
            >
                <div className="animate-[spin_5s_linear_infinite] bg-[conic-gradient(from_90deg_at_50%_50%,#F76363_0%,#3D65F5_100%)] w-[300px] h-full"></div>
                <div className="animate-[spin_10s_linear_infinite] bg-[conic-gradient(from_90deg_at_50%_50%,#C11A1A_0%,#002AC4_100%)] w-[300px] h-full"></div>
            </div>
            <div
                className={
                    'w-full max-w-xl space-y-4 transition-all duration-1000' +
                    (hasAnyDomains ? ' -mt-[450px]' : ' -mt-[200px]')
                }
            >
                <h1 className="text-4xl font-semibold text-center tracking-tight flex flex-col">
                    <span>Generate domain names</span>
                    <span>that are guaranteed available</span>
                </h1>
                <p className="text-center font-light tracking-tight">
                    Get domain options based on your idea that are available to
                    register
                </p>
            </div>

            <div className="w-full max-w-xl space-y-4 mt-6 bg-white p-3 rounded-xl backdrop-blur-md bg-opacity-70 border border-neutral-300">
                <div className="relative overflow-hidden p-[1px] rounded-xl group">
                    <form
                        onSubmit={handleSuggestStream}
                        className="flex border border-[#D9D9D9] px-4 py-2 text-sm justify-between rounded-xl bg-white"
                    >
                        <input
                            placeholder="Describe your app, service, or company idea..."
                            value={userInput}
                            onChange={(e) => setUserInput(e.target.value)}
                            className="w-full outline-none bg-transparent"
                        />
                        <button
                            type="submit"
                            className="pl-4 pr-2 border-l border-[#D9D9D9] bg-transparent"
                            disabled={isLoading}
                        >
                            {isLoading ? '...' : 'Go'}
                        </button>
                    </form>
                    <span className="absolute inset-[-1000%] animate-[spin_5s_linear_infinite] bg-[conic-gradient(from_90deg_at_50%_50%,#FFB9B9_0%,#E3CBE9_50%,#9FB3FF_100%)] -z-10 opacity-0 group-focus-within:opacity-100" />
                </div>

                {errorMsg && (
                    <div className="mt-2 text-red-500">
                        <strong>Error:</strong> {errorMsg}
                    </div>
                )}

                {hasAnyDomains && (
                    <div className="pt-3 space-y-4">
                        {freeDomains.length > 0 && (
                            <details open>
                                <summary className="cursor-pointer text-sm font-semibold mb-2 ml-2">
                                    Available Domains ({freeDomains.length})
                                </summary>
                                <ul className="mt-2 space-y-2">
                                    {freeDomains.map(renderDomainRow)}
                                </ul>
                            </details>
                        )}

                        {registeredDomains.length > 0 && (
                            <details>
                                <summary className="cursor-pointer text-sm font-semibold mb-2 ml-2">
                                    Registered Domains (
                                    {registeredDomains.length})
                                </summary>
                                <ul className="mt-2 space-y-2">
                                    {registeredDomains.map(renderDomainRow)}
                                </ul>
                            </details>
                        )}

                        {unknownDomains.length > 0 && (
                            <details>
                                <summary className="cursor-pointer text-sm font-semibold mb-2 ml-2">
                                    Other ({unknownDomains.length})
                                </summary>
                                <ul className="mt-2 space-y-2">
                                    {unknownDomains.map(renderDomainRow)}
                                </ul>
                            </details>
                        )}
                    </div>
                )}
            </div>

            <div className="w-full max-w-xl space-y-4 mt-48 text-left">
                <h2 className="text-2xl font-semibold tracking-tight flex flex-col">
                    <span>Get many suggestions</span>
                    <span>
                        and iterations for your
                        <FlipWords words={flipwords} />
                    </span>
                </h2>
                <p className="font-light tracking-tight text-balance">
                    Choosing a great domain name is often the first step in
                    bringing your business, app, or project to life. Our AI
                    takes your input and quickly provides available domain
                    names. This means you can skip the guesswork and go straight
                    to securing a name that fits your brand and vision.
                </p>
            </div>
            <div className="w-full max-w-xl space-y-4 mt-48 text-right">
                <h2 className="text-2xl font-semibold tracking-tight flex flex-col">
                    How it works
                </h2>
                <p className="font-light tracking-tight text-balance">
                    Describe your app, service, or company idea in the search
                    bar. Click "Go" and our AI will generate available domain
                    names based on your input. You get 5 available domain names
                    and more that are registered for inspiration or to help you
                    find similar names.
                </p>
            </div>
        </main>
    );
}

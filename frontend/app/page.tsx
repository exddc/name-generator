'use client';

import React, { useState } from 'react';
import { Button } from '@/components/ui/button';
import { Textarea } from '@/components/ui/textarea';

interface DomainData {
    domain: string;
    status: string;
}

export default function Home() {
    const [userInput, setUserInput] = useState('');
    const [domains, setDomains] = useState<DomainData[]>([]);
    const [errorMsg, setErrorMsg] = useState<string | null>(null);
    const [isLoading, setIsLoading] = useState(false);

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

    return (
        <main className="flex flex-col items-center justify-center pt-48">
            <div className="bg-gradient-to-b from-[#C11A1A] to-[#002AC4] h-[200px] w-96 blur-[120px] -z-10"></div>
            <div className="w-full max-w-xl space-y-4 -mt-[250px]">
                <h1 className="text-4xl font-semibold text-center tracking-tight flex flex-col">
                    <span>Generate domain names</span>
                    <span>that are guaranteed available</span>
                </h1>
                <p className="text-center font-light tracking-tight">
                    Brainstorm with AI and get high quality domains now:
                </p>
            </div>
            <div className="w-full max-w-xl space-y-4 mt-6">
                <form
                    onSubmit={handleSuggestStream}
                    className="flex border border-[#D9D9D9] px-4 py-2 rounded-xl text-sm justify-between bg-white focus-within:ring-1 focus-within:ring-purple-500 focus-within:shadow-sm focus-within:shadow-purple-700"
                >
                    <input
                        placeholder="Describe your app, service, or company idea..."
                        value={userInput}
                        onChange={(e) => setUserInput(e.target.value)}
                        className="w-full outline-none bg-white"
                    />
                    <button
                        type="submit"
                        className="pl-4 pr-2 border-l border-[#D9D9D9] bg-white"
                        disabled={isLoading}
                    >
                        {isLoading ? '...' : 'Go'}
                    </button>
                </form>

                {errorMsg && (
                    <div className="mt-2 text-red-500">
                        <strong>Error:</strong> {errorMsg}
                    </div>
                )}

                {domains.length > 0 && (
                    <div className="mt-6">
                        <ul className="grid grid-cols-1 gap-1">
                            {domains.map((item, index) => (
                                <li
                                    key={index}
                                    className="flex border border-[#D9D9D9] px-4 py-2 rounded-xl text-sm justify-between bg-white"
                                >
                                    <a
                                        href={'https://' + item.domain}
                                        target="_blank"
                                        className=""
                                    >
                                        {item.domain}
                                    </a>
                                    <div className="flex gap-4 items-center">
                                        <p
                                            className={
                                                (item.status == 'free'
                                                    ? 'bg-green-300 border-green-800'
                                                    : item.status ==
                                                      'registered'
                                                    ? 'bg-red-300 border-red-800'
                                                    : 'bg-yellow-200 border-yellow-800') +
                                                ' text-black font-semibold text-xs border px-2 flex items-center h-fit rounded-xl'
                                            }
                                        >
                                            {item.status == 'free'
                                                ? 'Available'
                                                : item.status == 'registered'
                                                ? 'Registered'
                                                : 'Unknown'}
                                        </p>
                                        <button
                                            className="pl-4 pr-2 border-l border-[#D9D9D9] bg-white"
                                            disabled={isLoading}
                                        >
                                            {isLoading
                                                ? '...'
                                                : 'Generate similar'}
                                        </button>
                                    </div>
                                </li>
                            ))}
                        </ul>
                    </div>
                )}
            </div>
            <div className="w-full max-w-xl space-y-4 mt-48">
                <h2 className="text-2xl font-semibold text-center tracking-tight flex flex-col">
                    <span>Get many suggestions and iterations</span>
                    <span>for your project, app, idea ...</span>
                </h2>
                <p className="text-center font-light tracking-tight text-balance">
                    Having a high quality domain will help you generate more
                    leads and be easily recognised
                </p>
            </div>
            <div className="w-full max-w-xl space-y-4 mt-48">
                <h2 className="text-2xl font-semibold text-center tracking-tight flex flex-col text-balance">
                    High quality domains are key to success in the digital world
                </h2>
                <p className="text-center font-light tracking-tight text-balance">
                    Get started now and generate domain names that are
                    guaranteed available
                </p>
            </div>
        </main>
    );
}

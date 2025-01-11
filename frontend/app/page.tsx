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
        <main className="flex flex-col items-center justify-center p-24">
            <div className="w-full max-w-xl space-y-4">
                <h1 className="text-4xl font-medium text-center tracking-tighter text-balance">
                    Generate domain names that are guaranteed available
                </h1>
                <p className="text-center font-thin tracking-tighter">
                    Brainstorm with AI and get high quality domains that are
                    definitely available
                </p>
            </div>
            <div className="w-full max-w-xl space-y-4 mt-8">
                <form
                    onSubmit={handleSuggestStream}
                    className="flex border border-[#D9D9D9]"
                >
                    <input
                        placeholder="Describe your app, service, or company idea..."
                        value={userInput}
                        onChange={(e) => setUserInput(e.target.value)}
                        className="min-h-[100px]"
                    />
                    <button
                        type="submit"
                        className="w-full"
                        disabled={isLoading}
                    >
                        {isLoading ? 'Generating...' : 'Generate Domain Names'}
                    </button>
                </form>

                {errorMsg && (
                    <div className="mt-2 text-red-500">
                        <strong>Error:</strong> {errorMsg}
                    </div>
                )}

                {domains.length > 0 && (
                    <div className="mt-4">
                        <h2 className="text-lg font-semibold">
                            Suggested Domains:
                        </h2>
                        <ul className="mt-2 grid grid-cols-1 gap-1">
                            {domains.map((item, index) => (
                                <li
                                    key={index}
                                    className="border border-neutral-200 rounded-lg p-2 flex justify-between items-center"
                                >
                                    <a
                                        href={'https://' + item.domain}
                                        target="_blank"
                                        className="font-bold"
                                    >
                                        {item.domain}
                                    </a>
                                    <p
                                        className={
                                            item.status == 'free'
                                                ? 'text-green-600'
                                                : item.status == 'registered'
                                                ? 'text-red-600'
                                                : 'text-yellow-600'
                                        }
                                    >
                                        {item.status}
                                    </p>
                                </li>
                            ))}
                        </ul>
                    </div>
                )}
            </div>
        </main>
    );
}

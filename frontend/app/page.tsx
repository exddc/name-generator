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

    /**
     * Opens an EventSource connection to:
     *   http://0.0.0.0:8000/suggest_stream?query={your-query}
     * Listens for SSE events: domain_suggestion, error, done.
     */
    const handleSuggestStream = (e: React.FormEvent) => {
        e.preventDefault();
        setIsLoading(true);
        setDomains([]);
        setErrorMsg(null);

        // Build the SSE URL with query param
        const url = `http://0.0.0.0:8000/suggest_stream?query=${encodeURIComponent(
            userInput
        )}`;

        // Create an EventSource
        const evtSource = new EventSource(url);

        evtSource.onopen = () => {
            console.log('SSE connection opened.');
        };

        // If an error occurs at the network-level, this fires
        evtSource.onerror = (err) => {
            console.error('SSE onerror triggered:', err);
            setErrorMsg(
                'A network or server error occurred while streaming data.'
            );
            setIsLoading(false);
            evtSource.close();
        };

        // The "default" event if the server sends data without an "event:" field
        evtSource.onmessage = (e) => {
            console.log('Generic message:', e.data);
            // We don't expect generic messages if we always specify "event:" in the backend
        };

        // Listen for named events
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
            // The server might be sending an SSE event named "error"
            console.error('SSE error event:', e.data);
            setErrorMsg(e.data ?? 'Unknown error occurred.');
        });

        evtSource.addEventListener('done', (e: MessageEvent) => {
            console.log('SSE done event:', e.data);
            // We can do cleanup or show a "finished" message
            setIsLoading(false);
            evtSource.close(); // Stop listening
        });
    };

    return (
        <main className="flex min-h-screen flex-col items-center justify-center p-24">
            <div className="w-full max-w-md space-y-4">
                <h1 className="text-2xl font-bold text-center">
                    Domain Name Generator (SSE)
                </h1>

                <form onSubmit={handleSuggestStream} className="space-y-4">
                    <Textarea
                        placeholder="Describe your app, service, or company idea..."
                        value={userInput}
                        onChange={(e) => setUserInput(e.target.value)}
                        className="min-h-[100px]"
                    />
                    <Button
                        type="submit"
                        className="w-full"
                        disabled={isLoading}
                    >
                        {isLoading
                            ? 'Generating...'
                            : 'Generate Domain Names (Stream)'}
                    </Button>
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
                        <ul className="list-disc list-inside mt-2">
                            {domains.map((item, index) => (
                                <li key={index}>
                                    <strong>{item.domain}</strong> —{' '}
                                    {item.status}
                                </li>
                            ))}
                        </ul>
                    </div>
                )}
            </div>
        </main>
    );
}

'use client';

import { useState } from 'react';
import { Button } from '@/components/ui/button';
import { Textarea } from '@/components/ui/textarea';
import { suggestDomains, DomainResponse } from './actions';

export default function Home() {
    const [userInput, setUserInput] = useState('');
    const [domains, setDomains] = useState<DomainResponse[]>([]);
    const [isLoading, setIsLoading] = useState(false);

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault();
        setIsLoading(true);

        try {
            const response = await suggestDomains(userInput);

            // response is an array of DomainResponse objects
            // e.g. [{ domain: "example.com", status: "free" }, ...]
            if (Array.isArray(response)) {
                setDomains(response);
            } else {
                console.error('Invalid response format:', response);
                setDomains([]);
            }
        } catch (error) {
            console.error('Error in handleSubmit:', error);
            setDomains([]);
        } finally {
            setIsLoading(false);
        }
    };

    return (
        <main className="flex min-h-screen flex-col items-center justify-center p-24">
            <div className="w-full max-w-md space-y-4">
                <h1 className="text-2xl font-bold text-center">
                    Domain Name Generator
                </h1>
                <form onSubmit={handleSubmit} className="space-y-4">
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
                        {isLoading ? 'Generating...' : 'Generate Domain Names'}
                    </Button>
                </form>

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

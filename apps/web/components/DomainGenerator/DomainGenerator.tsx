'use client';

// Libraries
import React, { useEffect, useState } from 'react';
import { DomainData } from '@/lib/types';

// Components
import { DomainRow } from '@/components/DomainGenerator';
import { LoadingAnimation, LoadingAnimation2 } from '../Icons';

// Constants
const DOMAIN_SUGGESTION_URL = `${process.env.NEXT_PUBLIC_API_URL}/v1/domain`;

// Props
type DomainGeneratorProps = {
    onDomainsStatusChange?: (hasDomains: boolean) => void;
};

export default function DomainGenerator({
    onDomainsStatusChange,
}: DomainGeneratorProps) {
    const [userInput, setUserInput] = useState('');
    const [domains, setDomains] = useState<DomainData[]>([]);
    const [errorMsg, setErrorMsg] = useState<string | null>(null);
    const [isLoading, setIsLoading] = useState(false);
    const [textAreaRows, setTextAreaRows] = useState(1);
    const [freeDomains, setFreeDomains] = useState<DomainData[]>([]);
    const [registeredDomains, setRegisteredDomains] = useState<DomainData[]>(
        []
    );
    const [unknownDomains, setUnknownDomains] = useState<DomainData[]>([]);

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault();
        setIsLoading(true);
        setDomains([]);
        setErrorMsg(null);

        const response = await fetch(DOMAIN_SUGGESTION_URL, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ description: userInput }),
        });

        if (!response.ok) {
            const errorData = await response.json();
            setErrorMsg(errorData.message || 'Failed to generate domains.');
        } else {
            const data = await response.json();
            setDomains(data.suggestions);
            setFreeDomains(
                data.suggestions.filter((d: DomainData) => d.status === 'free')
            );
            setRegisteredDomains(
                data.suggestions.filter(
                    (d: DomainData) => d.status === 'registered'
                )
            );
            setUnknownDomains(
                data.suggestions.filter(
                    (d: DomainData) =>
                        d.status !== 'free' && d.status !== 'registered'
                )
            );
        }
        setIsLoading(false);
    };

    useEffect(() => {
        onDomainsStatusChange?.(domains.length > 0);
    }, [domains, onDomainsStatusChange]);

    return (
        <div
            id="domain-generator-form"
            className="w-full max-w-2xl space-y-4 mt-6 bg-white p-5 rounded-2xl backdrop-blur-lg bg-opacity-40 border border-neutral-200 transition-all duration-300"
        >
            <div className="relative overflow-hidden rounded-xl focus-within:ring-1 focus-within:ring-neutral-300">
                <form
                    onSubmit={handleSubmit}
                    className="flex border border-[#D9D9D9] px-4 py-3 text-base justify-between rounded-xl bg-white"
                >
                    <textarea
                        placeholder="Describe your app, service, or company idea..."
                        value={userInput}
                        onChange={(e) => {
                            setUserInput(e.target.value);
                            setTextAreaRows(
                                Math.min(
                                    Math.max(1, e.target.value.length / 50 + 1),
                                    10
                                )
                            );
                        }}
                        className="w-full outline-none bg-transparent pr-4"
                        rows={textAreaRows}
                        style={{ resize: 'none' }}
                        onKeyDown={(e) => {
                            if (e.key === 'Enter' && !e.shiftKey) {
                                e.preventDefault();
                                handleSubmit(e);
                            }
                        }}
                    />
                    <button
                        type="submit"
                        className="pl-4 pr-2 border-l border-[#D9D9D9] bg-transparent"
                        disabled={isLoading}
                    >
                        <span
                            className="flex items-center justify-center"
                            style={{ width: 24, height: 14 }}
                        >
                            {isLoading ? <LoadingAnimation2 /> : 'Go'}
                        </span>
                    </button>
                </form>
            </div>

            {domains.length > 0 && (
                <div className="w-full flex items-center justify-center">
                    <button
                        onClick={() => {}} // TODO: get more domains
                        className="text-xs hover:cursor-pointer bg-white border-gray-400 px-2 py-1 rounded-lg backdrop-blur-lg bg-opacity-60 hover:bg-opacity-100 hover:shadow-sm transition-all duration-300 hover:border-gray-600"
                    >
                        Generate more Suggestions
                    </button>
                </div>
            )}

            {errorMsg && (
                <div className="mt-2 text-red-500">
                    <strong>Error:</strong> {errorMsg}
                </div>
            )}

            {domains.length > 0 && (
                <div className="pt-3 space-y-4">
                    {freeDomains.length > 0 && (
                        <details open>
                            <summary className="cursor-pointer text-sm font-semibold mb-2 ml-2">
                                Available Domains ({freeDomains?.length})
                            </summary>
                            <div className="mt-2 space-y-2">
                                {freeDomains.map((domain) => (
                                    <DomainRow
                                        domain={domain}
                                        key={domain.domain + '-free-domain'}
                                    />
                                ))}
                            </div>
                        </details>
                    )}

                    {registeredDomains.length > 0 && (
                        <details>
                            <summary className="cursor-pointer text-sm font-semibold mb-2 ml-2">
                                Registered Domains ({registeredDomains?.length})
                            </summary>
                            <div className="mt-2 space-y-2">
                                {registeredDomains.map((domain) => (
                                    <DomainRow
                                        domain={domain}
                                        key={
                                            domain.domain + '-registered-domain'
                                        }
                                    />
                                ))}
                            </div>
                        </details>
                    )}

                    {unknownDomains.length > 0 && (
                        <details
                            open={
                                freeDomains.length == 0 &&
                                registeredDomains.length == 0
                            }
                        >
                            <summary className="cursor-pointer text-sm font-semibold mb-2 ml-2">
                                Other ({unknownDomains?.length})
                            </summary>
                            <div className="mt-2 space-y-2">
                                {unknownDomains.map((domain) => (
                                    <DomainRow
                                        domain={domain}
                                        key={domain.domain + '-unknown-domain'}
                                    />
                                ))}
                            </div>
                        </details>
                    )}
                </div>
            )}
        </div>
    );
}

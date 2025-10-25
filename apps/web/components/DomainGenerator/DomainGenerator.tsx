'use client';

// Libraries
import React, { useEffect, useRef, useState } from 'react';
import { AnimatePresence, motion } from 'motion/react';
import { Domain, DomainStatus, StreamMessage } from '@/lib/types';

// Components
import { DomainRow } from '@/components/DomainGenerator';
import { LoadingAnimation2 } from '../Icons';
import { CircleStop, SendHorizonal, Square } from 'lucide-react';

// Constants
const DOMAIN_SUGGESTION_URL = `${process.env.NEXT_PUBLIC_API_URL}/v1/domain/stream`;

// Props
type DomainGeneratorProps = {
    onDomainsStatusChange?: (hasDomains: boolean) => void;
};

export default function DomainGenerator({
    onDomainsStatusChange,
}: DomainGeneratorProps) {
    const [userInput, setUserInput] = useState('');
    const [domains, setDomains] = useState<Domain[]>([]);
    const [errorMsg, setErrorMsg] = useState<string | null>(null);
    const [isLoading, setIsLoading] = useState(false);
    const [textAreaRows, setTextAreaRows] = useState(1);

    // Domain Filters
    const [freeDomains, setFreeDomains] = useState<Domain[]>([]);
    const [registeredDomains, setRegisteredDomains] = useState<Domain[]>([]);
    const [unknownDomains, setUnknownDomains] = useState<Domain[]>([]);

    const abortControllerRef = useRef<AbortController | null>(null);

    const applySuggestionMessage = (message: StreamMessage) => {
        setDomains((prev) => {
            const next = [...prev];

            const upsert = (items?: Domain[]) => {
                if (!items?.length) return;
                for (const item of items) {
                    const existingIndex = next.findIndex(
                        (domain) => domain.domain === item.domain
                    );

                    if (existingIndex >= 0) {
                        next[existingIndex] = item;
                    } else {
                        next.push(item);
                    }
                }
            };

            upsert(message.new);
            upsert(message.updates);
            upsert(message.suggestions);

            return next;
        });
    };

    const handleCancel = () => {
        abortControllerRef.current?.abort();
    };

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault();
        abortControllerRef.current?.abort();

        const controller = new AbortController();
        abortControllerRef.current = controller;

        setIsLoading(true);
        setDomains([]);
        setErrorMsg(null);

        try {
            const response = await fetch(DOMAIN_SUGGESTION_URL, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ description: userInput }),
                signal: controller.signal,
            });

            if (!response.ok || !response.body) {
                const errorData = await response.json().catch(() => ({}));
                throw new Error(
                    errorData.message || 'Failed to generate domains.'
                );
            }

            const reader = response.body.getReader();
            const decoder = new TextDecoder();
            let buffer = '';
            let isStreamComplete = false;

            while (true) {
                const { done, value } = await reader.read();
                if (done) break;
                buffer += decoder.decode(value, { stream: true });

                const eventBlocks = buffer.split('\n\n');
                buffer = eventBlocks.pop() ?? '';

                for (const block of eventBlocks) {
                    if (!block.trim()) {
                        continue;
                    }

                    const lines = block.split('\n');
                    let eventName = '';
                    const dataLines: string[] = [];

                    for (const rawLine of lines) {
                        const line = rawLine.trimEnd();
                        if (!line) continue;

                        if (line.startsWith('event:')) {
                            eventName = line.slice('event:'.length).trim();
                        } else if (line.startsWith('data:')) {
                            dataLines.push(
                                line.slice('data:'.length).trimStart()
                            );
                        }
                    }

                    if (!eventName) {
                        continue;
                    }

                    const dataRaw = dataLines.join('\n') || '{}';
                    let payload: StreamMessage | undefined;

                    try {
                        payload = JSON.parse(dataRaw) as StreamMessage;
                    } catch (jsonError) {
                        console.warn(
                            'Failed to parse stream payload',
                            jsonError
                        );
                        payload = undefined;
                    }

                    switch (eventName) {
                        case 'suggestions':
                            if (payload) {
                                applySuggestionMessage(payload);
                            }
                            break;
                        case 'complete':
                            if (payload) {
                                applySuggestionMessage(payload);
                            }
                            isStreamComplete = true;
                            break;
                        case 'error':
                            if (payload && 'message' in payload) {
                                setErrorMsg(String((payload as any).message));
                            } else {
                                setErrorMsg('Failed to generate domains.');
                            }
                            isStreamComplete = true;
                            break;
                        default:
                            // ignore other events (start, heartbeat, etc.)
                            break;
                    }

                    if (isStreamComplete) {
                        break;
                    }
                }

                if (isStreamComplete) {
                    break;
                }
            }
        } catch (error) {
            if (
                !(error instanceof DOMException && error.name === 'AbortError')
            ) {
                console.error(error);
                setErrorMsg(
                    error instanceof Error
                        ? error.message
                        : 'Failed to generate domains.'
                );
            }
        } finally {
            setIsLoading(false);
        }
    };

    useEffect(() => {
        setFreeDomains(
            domains.filter((d) => d.status === DomainStatus.AVAILABLE)
        );
        setRegisteredDomains(
            domains.filter((d) => d.status === DomainStatus.REGISTERED)
        );
        setUnknownDomains(
            domains.filter((d) => d.status === DomainStatus.UNKNOWN)
        );
    }, [domains]);

    useEffect(() => {
        onDomainsStatusChange?.(domains.length > 0);
    }, [domains, onDomainsStatusChange]);

    return (
        <div
            id="domain-generator-form"
            className="w-full max-w-2xl space-y-4 mt-6 bg-white p-5 rounded-2xl backdrop-blur-lg bg-opacity-40 border border-neutral-200 transition-all duration-500"
        >
            <div className="relative overflow-hidden rounded-xl focus-within:ring-1 focus-within:ring-neutral-300">
                <form className="flex border border-[#D9D9D9] px-4 py-3 text-base justify-between rounded-xl bg-white">
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
                        type="button"
                        onClick={isLoading ? handleCancel : handleSubmit}
                        className="pl-4 pr-2 border-l border-[#D9D9D9] bg-transparent"
                    >
                        <span
                            className="flex items-center justify-center hover:cursor-pointer hover:scale-110 transition-all duration-300"
                            style={{ width: 24, height: 14 }}
                        >
                            {isLoading ? (
                                <Square className="size-5" strokeWidth={1.5} />
                            ) : (
                                <SendHorizonal
                                    className="size-5"
                                    strokeWidth={1.5}
                                />
                            )}
                        </span>
                    </button>
                </form>
            </div>

            <AnimatePresence>
                {isLoading ? (
                    <motion.div
                        key="domain-loading-indicator"
                        initial={{ height: 0, opacity: 0 }}
                        animate={{ height: 'auto', opacity: 1 }}
                        exit={{ height: 'auto', opacity: 0 }}
                        transition={{ duration: 0.2, ease: 'easeInOut' }}
                        className="w-full overflow-hidden"
                    >
                        <span className="flex items-center justify-center text-xs py-1 animate-pulse">
                            Generating domains...
                        </span>
                    </motion.div>
                ) : !isLoading && domains.length > 0 ? (
                    <motion.div
                        key="generate-more-domains"
                        initial={{ opacity: 0 }}
                        animate={{ opacity: 1 }}
                        exit={{ opacity: 0 }}
                        transition={{
                            delay: 0.2,
                            duration: 0.2,
                            ease: 'easeInOut',
                        }}
                        className="w-full flex items-center justify-center"
                    >
                        <button
                            onClick={() => {}}
                            className="text-xs hover:cursor-pointer bg-white border-gray-400 px-2 py-1 rounded-lg backdrop-blur-lg bg-opacity-60 hover:bg-opacity-100 hover:shadow-sm transition-all duration-300 hover:border-gray-600"
                        >
                            Generate more Suggestions
                        </button>
                    </motion.div>
                ) : null}
            </AnimatePresence>

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

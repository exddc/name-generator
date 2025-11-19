'use client';

// Libraries
import React, { useEffect, useRef, useState } from 'react';
import { AnimatePresence, motion } from 'motion/react';
import { Domain, DomainStatus, StreamMessage } from '@/lib/types';
import { useSession } from '@/lib/auth-client';
import { usePlausible } from 'next-plausible';

// Components
import DomainSection from './DomainSection';
import { SendHorizonal, Square } from 'lucide-react';
import { Button } from '../ui/button';

// Constants
const DOMAIN_SUGGESTION_URL = `${process.env.NEXT_PUBLIC_API_URL}/v1/domain/stream`;

// Props
type DomainGeneratorProps = {
    onDomainsStatusChange?: (hasDomains: boolean) => void;
    initialSearch?: string;
};

export default function DomainGenerator({
    onDomainsStatusChange,
    initialSearch,
}: DomainGeneratorProps) {
    const plausible = usePlausible();
    const { data: session } = useSession();
    const [userInput, setUserInput] = useState(initialSearch || '');
    const [domains, setDomains] = useState<Domain[]>([]);
    const [errorMsg, setErrorMsg] = useState<string | null>(null);
    const [isLoading, setIsLoading] = useState(false);
    const [textAreaRows, setTextAreaRows] = useState(1);
    const [loadingStartTime, setLoadingStartTime] = useState<number | null>(
        null
    );
    const [hasReceivedFirstResponse, setHasReceivedFirstResponse] =
        useState(false);
    const [firstResponseTime, setFirstResponseTime] = useState<number | null>(
        null
    );
    const [loadingText, setLoadingText] = useState('Generating domains...');

    // Domain Filters
    const [freeDomains, setFreeDomains] = useState<Domain[]>([]);
    const [registeredDomains, setRegisteredDomains] = useState<Domain[]>([]);
    const [unknownDomains, setUnknownDomains] = useState<Domain[]>([]);

    const abortControllerRef = useRef<AbortController | null>(null);

    // Collapsible state for sections
    const [isFreeOpen, setIsFreeOpen] = useState(true);
    const [isRegisteredOpen, setIsRegisteredOpen] = useState(false);
    const [isUnknownOpen, setIsUnknownOpen] = useState(false);

    // Update userInput when initialSearch changes
    useEffect(() => {
        if (initialSearch) {
            setUserInput(initialSearch);
        }
    }, [initialSearch]);

    // Set textAreaRows based on window width after mount
    useEffect(() => {
        const updateTextAreaRows = () => {
            setTextAreaRows(window.innerWidth < 768 ? 2 : 1);
        };

        updateTextAreaRows();
        window.addEventListener('resize', updateTextAreaRows);

        return () => {
            window.removeEventListener('resize', updateTextAreaRows);
        };
    }, []);

    const applySuggestionMessage = (message: StreamMessage) => {
        setDomains((prev) => {
            const next = [...prev];
            let hasNewDomains = false;

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
                        hasNewDomains = true;
                    }
                }
            };

            upsert(message.new);
            upsert(message.updates);
            upsert(message.suggestions);

            if (hasNewDomains && !hasReceivedFirstResponse) {
                setHasReceivedFirstResponse(true);
                setFirstResponseTime(Date.now());
            }

            return next;
        });
    };

    const handleCancel = () => {
        abortControllerRef.current?.abort();
    };

    const fetchSuggestions = async (
        controller: AbortController,
        creative: boolean = false
    ) => {
        try {
            const requestBody: {
                description: string;
                user_id?: string;
                creative?: boolean;
            } = {
                description: userInput,
            };

            if (session?.user?.id) {
                requestBody.user_id = session.user.id;
            }

            if (creative) {
                requestBody.creative = true;
            }

            const response = await fetch(DOMAIN_SUGGESTION_URL, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify(requestBody),
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
                                setErrorMsg(String((payload as any).message)); // eslint-disable-line @typescript-eslint/no-explicit-any
                            } else {
                                setErrorMsg('Failed to generate domains.');
                            }
                            isStreamComplete = true;
                            break;
                        default:
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
            setLoadingStartTime(null);
            setFirstResponseTime(null);
        }
    };

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault();
        plausible('domain-generation-submit');
        abortControllerRef.current?.abort();

        const controller = new AbortController();
        abortControllerRef.current = controller;

        setIsLoading(true);
        setErrorMsg(null);
        setLoadingStartTime(Date.now());
        setHasReceivedFirstResponse(false);
        setFirstResponseTime(null);
        setLoadingText('Generating domains...');
        await fetchSuggestions(controller);
    };

    const handleGenerateMore = async (creative: boolean = false) => {
        abortControllerRef.current?.abort();

        const controller = new AbortController();
        abortControllerRef.current = controller;
        setIsLoading(true);
        setErrorMsg(null);
        setLoadingStartTime(Date.now());
        setHasReceivedFirstResponse(false);
        setFirstResponseTime(null);
        setLoadingText('Generating domains...');
        await fetchSuggestions(controller, creative);
    };

    useEffect(() => {
        if (!isLoading || loadingStartTime === null) {
            return;
        }

        const updateLoadingText = () => {
            const elapsed = Date.now() - loadingStartTime;

            if (elapsed >= 20000) {
                setLoadingText('This is a very tricky search...');
            } else if (
                hasReceivedFirstResponse &&
                firstResponseTime !== null &&
                Date.now() - firstResponseTime >= 4000
            ) {
                setLoadingText('Validating more domains...');
            } else if (hasReceivedFirstResponse) {
                setLoadingText('Generating more domains...');
            } else if (elapsed >= 3000) {
                setLoadingText('Validating domains...');
            } else {
                setLoadingText('Generating domains...');
            }
        };

        updateLoadingText();

        const interval = setInterval(updateLoadingText, 100);

        return () => clearInterval(interval);
    }, [
        isLoading,
        loadingStartTime,
        hasReceivedFirstResponse,
        firstResponseTime,
    ]);

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
        if (
            freeDomains.length === 0 &&
            registeredDomains.length === 0 &&
            unknownDomains.length > 0
        ) {
            setIsUnknownOpen(true);
        }
    }, [freeDomains.length, registeredDomains.length, unknownDomains.length]);

    useEffect(() => {
        onDomainsStatusChange?.(domains.length > 0);
    }, [domains, onDomainsStatusChange]);

    return (
        <div
            id="domain-generator-form"
            className="w-full max-w-2xl space-y-4 mt-6 bg-white p-5 rounded-2xl backdrop-blur-lg bg-opacity-40 border border-neutral-200 transition-all duration-300"
        >
            <div className="flex items-center text-xs text-neutral-500 w-full justify-center">
                <span className="font-semibold text-black bg-neutral-50 px-3 py-1 rounded-l-lg border border-neutral-300 hover:cursor-pointer hover:bg-neutral-100 transition-all duration-300 hover:text-neutral-800 hover:shadow-sm">
                    Domain
                </span>
                <span className=" bg-neutral-100 bg-opacity-40 backdrop-blur-lg px-3 py-1 rounded-r-lg border border-l-0 border-neutral-300 hover:cursor-pointer hover:bg-neutral-50 transition-all duration-300 hover:text-neutral-800 hover:shadow-sm">
                    Social Media (coming soon)
                </span>
            </div>
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

            <AnimatePresence mode="wait">
                {isLoading ? (
                    <motion.div
                        key="domain-loading-indicator"
                        initial={{ opacity: 0, height: 0 }}
                        animate={{ opacity: 1, height: 'auto' }}
                        exit={{ opacity: 0, height: 0 }}
                        transition={{ duration: 0.2, ease: 'easeOut' }}
                        className="w-full overflow-hidden"
                    >
                        <span className="flex items-center justify-center text-xs py-1 animate-pulse">
                            {loadingText}
                        </span>
                    </motion.div>
                ) : !isLoading && domains.length > 0 ? (
                    <motion.div
                        key="generate-more-domains"
                        initial={{ opacity: 0, height: 0 }}
                        animate={{ opacity: 1, height: 'auto' }}
                        exit={{ opacity: 0, height: 0 }}
                        transition={{ duration: 0.2, ease: 'easeOut' }}
                        className="w-full overflow-hidden flex items-center justify-center gap-4"
                    >
                        <Button
                            onClick={() => handleGenerateMore(false)}
                            size="sm"
                        >
                            Generate more
                        </Button>
                        <Button
                            onClick={() => handleGenerateMore(true)}
                            size="sm"
                        >
                            Get creative
                        </Button>
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
                    <DomainSection
                        title={`Available Domains (${freeDomains.length})`}
                        domains={freeDomains}
                        isOpen={isFreeOpen}
                        onToggle={() => setIsFreeOpen((v) => !v)}
                        itemKeySuffix="free"
                    />
                    <DomainSection
                        title={`Registered Domains (${registeredDomains.length})`}
                        domains={registeredDomains}
                        isOpen={isRegisteredOpen}
                        onToggle={() => setIsRegisteredOpen((v) => !v)}
                        itemKeySuffix="registered"
                    />
                    <DomainSection
                        title={`Other (${unknownDomains.length})`}
                        domains={unknownDomains}
                        isOpen={isUnknownOpen}
                        onToggle={() => setIsUnknownOpen((v) => !v)}
                        itemKeySuffix="unknown"
                    />
                </div>
            )}
        </div>
    );
}

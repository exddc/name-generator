'use client';

// Libraries
import React, { useEffect, useRef, useState, useCallback } from 'react';
import { AnimatePresence, motion } from 'motion/react';
import {
    Domain,
    DomainStatus,
    StreamMessage,
    ApiError,
    UserPreferencesInput,
} from '@/lib/types';
import { useSession } from '@/lib/auth-client';
import { usePlausible } from 'next-plausible';
import { toast } from '@/components/ui/sonner';

// Components
import DomainSection from './DomainSection';
import { SendHorizonal, Square, RefreshCw } from 'lucide-react';
import { Button } from '../ui/button';
import {
    InputGroup,
    InputGroupAddon,
    InputGroupTextarea,
} from '../ui/input-group';

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
    const [isLoading, setIsLoading] = useState(false);
    const [loadingStartTime, setLoadingStartTime] = useState<number | null>(
        null
    );
    const [hasReceivedFirstResponse, setHasReceivedFirstResponse] =
        useState(false);
    const [firstResponseTime, setFirstResponseTime] = useState<number | null>(
        null
    );
    const [loadingText, setLoadingText] = useState('Generating domains...');

    // Error state with retry capability
    const [lastError, setLastError] = useState<ApiError | null>(null);
    const [canRetry, setCanRetry] = useState(false);

    // Domain Filters
    const [freeDomains, setFreeDomains] = useState<Domain[]>([]);
    const [registeredDomains, setRegisteredDomains] = useState<Domain[]>([]);
    const [unknownDomains, setUnknownDomains] = useState<Domain[]>([]);

    // User votes for personalized suggestions
    const [domainVotes, setDomainVotes] = useState<Map<string, 1 | -1>>(
        new Map()
    );
    const [favoritedDomains, setFavoritedDomains] = useState<Set<string>>(
        new Set()
    );

    const abortControllerRef = useRef<AbortController | null>(null);
    const textareaRef = useRef<HTMLTextAreaElement>(null);

    // Collapsible state for sections
    const [isFreeOpen, setIsFreeOpen] = useState(true);
    const [isRegisteredOpen, setIsRegisteredOpen] = useState(false);
    const [isUnknownOpen, setIsUnknownOpen] = useState(false);

    // Handlers for votes and favorites
    const handleDomainVote = useCallback((domainName: string, vote: 1 | -1) => {
        setDomainVotes((prev) => {
            const next = new Map(prev);
            next.set(domainName, vote);
            return next;
        });
    }, []);

    const handleDomainFavorite = useCallback(
        (domainName: string, isFavorited: boolean) => {
            setFavoritedDomains((prev) => {
                const next = new Set(prev);
                if (isFavorited) {
                    next.add(domainName);
                } else {
                    next.delete(domainName);
                }
                return next;
            });
        },
        []
    );

    // Update userInput when initialSearch changes
    useEffect(() => {
        if (initialSearch) {
            setUserInput(initialSearch);
        }
    }, [initialSearch]);

    // Auto-resize textarea
    useEffect(() => {
        if (textareaRef.current) {
            textareaRef.current.style.height = 'auto';
            textareaRef.current.style.height = `${textareaRef.current.scrollHeight}px`;
        }
    }, [userInput]);

    const markNewDomainsRef = useRef(false);

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
                        next[existingIndex] = {
                            ...item,
                            isNew: next[existingIndex].isNew,
                        };
                    } else {
                        next.push({
                            ...item,
                            isNew: markNewDomainsRef.current,
                        });
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

    const handleApiError = useCallback((error: ApiError) => {
        setLastError(error);
        setCanRetry(error.retry_allowed);

        // Show toast notification based on error type
        toast.error(error.message, {
            description: error.details || undefined,
            duration: 5000,
        });
    }, []);

    const handleRetry = useCallback(() => {
        setLastError(null);
        setCanRetry(false);

        const controller = new AbortController();
        abortControllerRef.current = controller;

        setIsLoading(true);
        setLoadingStartTime(Date.now());
        setHasReceivedFirstResponse(false);
        setFirstResponseTime(null);
        setLoadingText('Retrying...');

        fetchSuggestionsInternal(controller, false);
    }, [userInput, session?.user?.id]); // eslint-disable-line react-hooks/exhaustive-deps

    const buildPreferences = (): UserPreferencesInput | undefined => {
        const likedDomains: string[] = [];
        const dislikedDomains: string[] = [];

        domainVotes.forEach((vote, domain) => {
            if (vote === 1) {
                likedDomains.push(domain);
            } else if (vote === -1) {
                dislikedDomains.push(domain);
            }
        });

        const favoritedDomainsArray = Array.from(favoritedDomains);

        if (
            likedDomains.length === 0 &&
            dislikedDomains.length === 0 &&
            favoritedDomainsArray.length === 0
        ) {
            return undefined;
        }

        return {
            liked_domains: likedDomains,
            disliked_domains: dislikedDomains,
            favorited_domains: favoritedDomainsArray,
        };
    };

    const fetchSuggestionsInternal = async (
        controller: AbortController,
        creative: boolean = false,
        usePersonalized: boolean = false
    ) => {
        try {
            const requestBody: {
                description: string;
                user_id?: string;
                creative?: boolean;
                personalized?: boolean;
                preferences?: UserPreferencesInput;
            } = {
                description: userInput,
            };

            if (session?.user?.id) {
                requestBody.user_id = session.user.id;
            }

            if (creative) {
                requestBody.creative = true;
            }

            if (usePersonalized) {
                const preferences = buildPreferences();
                if (preferences) {
                    requestBody.personalized = true;
                    requestBody.preferences = preferences;
                }
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
                let errorData: ApiError;
                try {
                    const rawError = await response.json();
                    errorData = rawError.detail || rawError;
                } catch {
                    errorData = {
                        error: true,
                        code: 'internal_error' as any, // eslint-disable-line @typescript-eslint/no-explicit-any
                        message:
                            'Failed to connect to the server. Please check your connection and try again.',
                        retry_allowed: true,
                    };
                }
                handleApiError(errorData);
                return;
            }

            const reader = response.body.getReader();
            const decoder = new TextDecoder();
            let buffer = '';
            let isStreamComplete = false;

            // Clear any previous errors on successful connection
            setLastError(null);
            setCanRetry(false);

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
                            if (payload) {
                                const errorPayload: ApiError = {
                                    error: true,
                                    code:
                                        payload.code ||
                                        ('internal_error' as any), // eslint-disable-line @typescript-eslint/no-explicit-any
                                    message:
                                        payload.message ||
                                        'Failed to generate domains.',
                                    details: payload.details,
                                    retry_allowed:
                                        payload.retry_allowed ?? true,
                                };
                                handleApiError(errorPayload);
                            } else {
                                handleApiError({
                                    error: true,
                                    code: 'internal_error' as any, // eslint-disable-line @typescript-eslint/no-explicit-any
                                    message: 'Failed to generate domains.',
                                    retry_allowed: true,
                                });
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
                handleApiError({
                    error: true,
                    code: 'internal_error' as any, // eslint-disable-line @typescript-eslint/no-explicit-any
                    message:
                        error instanceof Error &&
                        error.message.includes('fetch')
                            ? 'Unable to connect to the server. Please check your internet connection.'
                            : 'An unexpected error occurred. Please try again.',
                    retry_allowed: true,
                });
            }
        } finally {
            setIsLoading(false);
            setLoadingStartTime(null);
            setFirstResponseTime(null);
        }
    };

    const fetchSuggestions = async (
        controller: AbortController,
        creative: boolean = false,
        usePersonalized: boolean = false
    ) => {
        await fetchSuggestionsInternal(controller, creative, usePersonalized);
    };

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault();
        plausible('domain-generation-submit');
        abortControllerRef.current?.abort();

        const isSubsequentSearch = domains.length > 0;
        markNewDomainsRef.current = isSubsequentSearch;
        setDomains((prev) => prev.map((d) => ({ ...d, isNew: false })));

        const controller = new AbortController();
        abortControllerRef.current = controller;

        setIsLoading(true);
        setLastError(null);
        setCanRetry(false);
        setLoadingStartTime(Date.now());
        setHasReceivedFirstResponse(false);
        setFirstResponseTime(null);
        setLoadingText('Generating domains...');

        const usePersonalized =
            isSubsequentSearch &&
            (domainVotes.size > 0 || favoritedDomains.size > 0);
        await fetchSuggestions(controller, false, usePersonalized);
    };

    const handleGenerateMore = async (creative: boolean = false) => {
        abortControllerRef.current?.abort();

        markNewDomainsRef.current = true;
        setDomains((prev) => prev.map((d) => ({ ...d, isNew: false })));

        const controller = new AbortController();
        abortControllerRef.current = controller;
        setIsLoading(true);
        setLastError(null);
        setCanRetry(false);
        setLoadingStartTime(Date.now());
        setHasReceivedFirstResponse(false);
        setFirstResponseTime(null);
        setLoadingText('Generating domains...');

        const usePersonalized =
            !creative && (domainVotes.size > 0 || favoritedDomains.size > 0);
        await fetchSuggestions(controller, creative, usePersonalized);
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
            <div className="relative overflow-hidden rounded-2xl">
                <form
                    onSubmit={handleSubmit}
                    className="w-full rounded-2xl bg-white"
                >
                    <InputGroup className="rounded-2xl bg-white border border-neutral-200 shadow-sm h-auto overflow-hidden transition-all duration-200">
                        <InputGroupTextarea
                            ref={textareaRef}
                            placeholder="Describe your app, service, or company idea..."
                            value={userInput}
                            onChange={(e) => {
                                setUserInput(e.target.value);
                            }}
                            className="text-base bg-transparent resize-none pl-4 py-3 min-h-0"
                            rows={1}
                            onKeyDown={(e) => {
                                if (e.key === 'Enter' && !e.shiftKey) {
                                    e.preventDefault();
                                    handleSubmit(e);
                                }
                            }}
                        />
                        <InputGroupAddon
                            align="inline-end"
                            className="pr-2 h-auto py-0 self-stretch flex items-center"
                        >
                            <button
                                type="button"
                                onClick={
                                    isLoading ? handleCancel : handleSubmit
                                }
                                className="px-4 bg-transparent h-full flex items-center justify-center outline-none focus:outline-none text-neutral-400 hover:text-neutral-600 transition-colors duration-200"
                            >
                                <span
                                    className="flex items-center justify-center hover:scale-110 transition-all duration-300"
                                    style={{ width: 24, height: 24 }}
                                >
                                    {isLoading ? (
                                        <Square
                                            className="size-5"
                                            strokeWidth={1.5}
                                            fill="currentColor"
                                            fillOpacity={0.2}
                                        />
                                    ) : (
                                        <SendHorizonal
                                            className="size-5"
                                            strokeWidth={1.5}
                                        />
                                    )}
                                </span>
                            </button>
                        </InputGroupAddon>
                    </InputGroup>
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
                ) : lastError && canRetry ? (
                    <motion.div
                        key="domain-error-retry"
                        initial={{ opacity: 0, height: 0 }}
                        animate={{ opacity: 1, height: 'auto' }}
                        exit={{ opacity: 0, height: 0 }}
                        transition={{ duration: 0.2, ease: 'easeOut' }}
                        className="w-full overflow-hidden flex flex-col items-center justify-center gap-2"
                    >
                        <Button
                            onClick={handleRetry}
                            size="sm"
                            variant="outline"
                            className="gap-2"
                        >
                            <RefreshCw className="size-4" />
                            Try Again
                        </Button>
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

            {domains.length > 0 && (
                <div className="pt-3 space-y-4">
                    <DomainSection
                        title={`Available Domains (${freeDomains.length})`}
                        domains={freeDomains}
                        isOpen={isFreeOpen}
                        onToggle={() => setIsFreeOpen((v) => !v)}
                        itemKeySuffix="free"
                        onVote={handleDomainVote}
                        onFavorite={handleDomainFavorite}
                    />
                    <DomainSection
                        title={`Registered Domains (${registeredDomains.length})`}
                        domains={registeredDomains}
                        isOpen={isRegisteredOpen}
                        onToggle={() => setIsRegisteredOpen((v) => !v)}
                        itemKeySuffix="registered"
                        onVote={handleDomainVote}
                        onFavorite={handleDomainFavorite}
                    />
                    <DomainSection
                        title={`Other (${unknownDomains.length})`}
                        domains={unknownDomains}
                        isOpen={isUnknownOpen}
                        onToggle={() => setIsUnknownOpen((v) => !v)}
                        itemKeySuffix="unknown"
                        onVote={handleDomainVote}
                        onFavorite={handleDomainFavorite}
                    />
                </div>
            )}
        </div>
    );
}

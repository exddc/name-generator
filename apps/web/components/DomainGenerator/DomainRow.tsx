'use client';

// Libraries
import React, { useEffect, useRef, useState } from 'react';
import { AnimatePresence, motion } from 'motion/react';
import {
    Domain,
    DomainStatusColor,
    RatingRequestBody,
    FavoriteRequestBody,
} from '@/lib/types';
import { cn, getAnonRandomId } from '@/lib/utils';
import { useSession } from '@/lib/auth-client';

// Components
import Link from 'next/link';
import {
    ChevronDown,
    Heart,
    ShoppingCart,
    ThumbsDown,
    ThumbsUp,
} from 'lucide-react';
import { Card } from '@/components/ui/card';
import { Button } from '../ui/button';

// Constants
const DOMAIN_VARIANTS_URL = `${process.env.NEXT_PUBLIC_API_URL}/v1/domain/variants/stream`;
const RATING_API_URL = `${process.env.NEXT_PUBLIC_API_URL}/v1/domain/rating`;
const RATINGS_GET_URL = `${process.env.NEXT_PUBLIC_API_URL}/v1/domain/rating`;
const FAVORITE_API_URL = `${process.env.NEXT_PUBLIC_API_URL}/v1/user/favorite`;

// Props
type DomainRowProps = {
    domain: Domain;
};

export default function DomainRow({ domain }: DomainRowProps) {
    const { data: session } = useSession();
    const [open, setOpen] = useState(false);
    const [loading, setLoading] = useState(false);
    const [variants, setVariants] = useState<Domain[]>([]);
    const [displayCount, setDisplayCount] = useState(5);
    const [fetchLimit, setFetchLimit] = useState(5);
    const [isStreamFinished, setIsStreamFinished] = useState(true);
    const [votingDomain, setVotingDomain] = useState<string | null>(null);
    const [domainVotes, setDomainVotes] = useState<Map<string, 1 | -1>>(
        new Map()
    );
    const [favoritedDomains, setFavoritedDomains] = useState<Set<string>>(
        new Set()
    );
    const [favoritingDomain, setFavoritingDomain] = useState<string | null>(
        null
    );

    const abortControllerRef = useRef<AbortController | null>(null);

    // Fetch existing ratings
    useEffect(() => {
        const fetchRatings = async () => {
            try {
                const params = new URLSearchParams();
                if (session?.user?.id) {
                    params.append('user_id', session.user.id);
                } else {
                    params.append('anon_random_id', getAnonRandomId());
                }
                params.append('page_size', '100'); // Fetch enough ratings

                const response = await fetch(
                    `${RATINGS_GET_URL}?${params.toString()}`
                );

                if (response.ok) {
                    const data = await response.json();
                    const votesMap = new Map<string, 1 | -1>();
                    data.ratings?.forEach(
                        (rating: { domain: string; vote: number }) => {
                            votesMap.set(rating.domain, rating.vote as 1 | -1);
                        }
                    );
                    setDomainVotes(votesMap);
                }
            } catch (error) {
                console.error('Failed to fetch ratings:', error);
            }
        };

        fetchRatings();
    }, [session?.user?.id]);

    // Fetch existing favorites
    useEffect(() => {
        const fetchFavorites = async () => {
            if (!session?.user?.id) {
                return; // Favorites require authentication
            }

            try {
                const params = new URLSearchParams();
                params.append('user_id', session.user.id);
                params.append('page_size', '100'); // Fetch enough favorites

                const response = await fetch(
                    `${FAVORITE_API_URL}?${params.toString()}`
                );

                if (response.ok) {
                    const data = await response.json();
                    const favoritesSet = new Set<string>();
                    data.favorites?.forEach((favorite: { domain: string }) => {
                        favoritesSet.add(favorite.domain);
                    });
                    setFavoritedDomains(favoritesSet);
                }
            } catch (error) {
                console.error('Failed to fetch favorites:', error);
            }
        };

        fetchFavorites();
    }, [session?.user?.id]);

    useEffect(() => {
        if (!open) {
            abortControllerRef.current?.abort();
            return;
        }

        // Prevent re-fetching on re-open if we already have the initial set of variants.
        if (variants.length > 0 && fetchLimit === 5) {
            return;
        }

        abortControllerRef.current?.abort();
        const controller = new AbortController();
        abortControllerRef.current = controller;

        const fetchVariants = async () => {
            setLoading(true);
            setIsStreamFinished(false);

            try {
                const domainName = domain.domain.split('.')[0];
                const response = await fetch(
                    `${DOMAIN_VARIANTS_URL}?domain_name=${domainName}&limit=${fetchLimit}`,
                    { signal: controller.signal }
                );

                if (!response.body) {
                    throw new Error('No response body');
                }

                const reader = response.body.getReader();
                const decoder = new TextDecoder();

                while (true) {
                    const { done, value } = await reader.read();
                    if (done) break;

                    const chunk = decoder.decode(value);
                    const lines = chunk
                        .split('\n')
                        .filter((line) => line.trim());

                    for (const line of lines) {
                        if (line.startsWith('event: suggestions')) {
                            const dataLine = lines.find((l) =>
                                l.startsWith('data:')
                            );
                            if (dataLine) {
                                const json = JSON.parse(dataLine.substring(5));
                                if (json.new) {
                                    setVariants((prev) => {
                                        const next = [...prev];
                                        for (const item of json.new) {
                                            const existingIndex =
                                                next.findIndex(
                                                    (d) =>
                                                        d.domain === item.domain
                                                );
                                            if (existingIndex < 0) {
                                                next.push(item);
                                            } else {
                                                next[existingIndex] = item;
                                            }
                                        }
                                        return next;
                                    });
                                }
                            }
                        } else if (line.startsWith('event: complete')) {
                            setIsStreamFinished(true);
                            setLoading(false);
                            return;
                        }
                    }
                }
            } catch (error) {
                if ((error as Error).name !== 'AbortError') {
                    console.error('Failed to fetch variants:', error);
                }
            } finally {
                if (!controller.signal.aborted) {
                    setLoading(false);
                    setIsStreamFinished(true);
                }
            }
        };

        fetchVariants();

        return () => {
            controller.abort();
        };
    }, [open, domain.domain, fetchLimit]);

    const handleShowMore = () => {
        setDisplayCount((prev) => prev + 5);
    };

    const handleGenerateMore = () => {
        setFetchLimit((prev) => prev + 5);
    };

    const canShowMoreLocal = displayCount < variants.length;
    const canGenerateMore = isStreamFinished && !loading;

    const handleVote = async (domain: string, vote: number) => {
        if (votingDomain === domain) {
            return;
        }

        setVotingDomain(domain);

        try {
            let requestBody: RatingRequestBody = {
                domain,
                vote: vote as 1 | -1,
            };

            if (session?.user?.id) {
                requestBody.user_id = session.user.id;
            } else {
                requestBody.anon_random_id = getAnonRandomId();
            }

            const response = await fetch(RATING_API_URL, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify(requestBody),
            });

            if (!response.ok) {
                const errorData = await response.json().catch(() => ({}));
                throw new Error(
                    errorData.detail ||
                        `Failed to submit vote: ${response.statusText}`
                );
            }

            const result = await response.json();

            // Update local vote state
            setDomainVotes((prev) => {
                const next = new Map(prev);
                next.set(domain, vote as 1 | -1);
                return next;
            });
        } catch (error) {
            console.error('Failed to submit vote:', error);
        } finally {
            setVotingDomain(null);
        }
    };

    const getVoteForDomain = (domainName: string): 1 | -1 | undefined => {
        return domainVotes.get(domainName);
    };

    const isDomainFavorited = (domainName: string): boolean => {
        return favoritedDomains.has(domainName);
    };

    const handleFavorite = async (domain: string) => {
        if (!session?.user?.id) {
            return;
        }

        if (favoritingDomain === domain) {
            return;
        }

        setFavoritingDomain(domain);

        try {
            const isFavorited = isDomainFavorited(domain);
            const action = isFavorited ? 'unfav' : 'fav';

            const requestBody: FavoriteRequestBody = {
                domain,
                user_id: session.user.id,
                action,
            };

            const response = await fetch(FAVORITE_API_URL, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify(requestBody),
            });

            if (!response.ok) {
                const errorData = await response.json().catch(() => ({}));
                throw new Error(
                    errorData.detail ||
                        `Failed to ${
                            action === 'fav' ? 'favorite' : 'unfavorite'
                        } domain: ${response.statusText}`
                );
            }

            setFavoritedDomains((prev) => {
                const next = new Set(prev);
                if (action === 'fav') {
                    next.add(domain);
                } else {
                    next.delete(domain);
                }
                return next;
            });
        } catch (error) {
            console.error('Failed to toggle favorite:', error);
        } finally {
            setFavoritingDomain(null);
        }
    };

    return (
        <Card className={cn('flex flex-col p-3 rounded-xl', open && 'gap-2')}>
            <div className="flex items-center justify-between">
                <div className="flex items-center gap-4">
                    <Link
                        href={'https://' + domain.domain}
                        target="_blank"
                        rel="noreferrer"
                        className="font-semibold"
                    >
                        {domain.domain}
                    </Link>
                    <span
                        className={cn(
                            DomainStatusColor[domain.status],
                            'text-neutral-800 font-semibold text-[0.4rem] border px-1 flex items-center h-[14px] rounded-xl'
                        )}
                    >
                        {domain.status}
                    </span>
                    <div className="flex items-center gap-1">
                        <button
                            className={cn(
                                'hover:cursor-pointer hover:scale-110 transition-all duration-300',
                                getVoteForDomain(domain.domain) === 1 &&
                                    'text-green-600'
                            )}
                            onClick={() => handleVote(domain.domain, 1)}
                        >
                            <ThumbsUp
                                className={cn(
                                    'size-3',
                                    getVoteForDomain(domain.domain) === 1 &&
                                        'text-green-600'
                                )}
                                strokeWidth={1.75}
                            />
                        </button>
                        <button
                            className={cn(
                                'hover:cursor-pointer hover:scale-110 transition-all duration-300',
                                getVoteForDomain(domain.domain) === -1 &&
                                    'text-red-600'
                            )}
                            onClick={() => handleVote(domain.domain, -1)}
                        >
                            <ThumbsDown
                                className={cn(
                                    'size-3',
                                    getVoteForDomain(domain.domain) === -1 &&
                                        'text-red-600'
                                )}
                                strokeWidth={1.75}
                            />
                        </button>
                    </div>
                </div>
                <div className="flex gap-4 items-center justify-end">
                    <button
                        type="button"
                        className={cn(
                            'hover:cursor-pointer hover:scale-110 transition-all duration-300',
                            isDomainFavorited(domain.domain) && 'text-red-600',
                            !session?.user?.id &&
                                'opacity-50 cursor-not-allowed'
                        )}
                        onClick={(e) => {
                            e.preventDefault();
                            e.stopPropagation();

                            handleFavorite(domain.domain);
                        }}
                        disabled={!session?.user?.id}
                    >
                        <Heart
                            className={cn(
                                'size-4 pointer-events-none',
                                isDomainFavorited(domain.domain) &&
                                    'text-red-600 fill-red-600'
                            )}
                            strokeWidth={1.75}
                            fill={
                                isDomainFavorited(domain.domain)
                                    ? 'currentColor'
                                    : 'none'
                            }
                        />
                    </button>
                    <button className="hover:cursor-pointer hover:scale-110 transition-all duration-300">
                        <ShoppingCart className="size-4" strokeWidth={1.75} />
                    </button>
                    <button
                        className="hover:cursor-pointer hover:scale-110 transition-all duration-300"
                        onClick={() => setOpen(!open)}
                    >
                        <ChevronDown
                            className={cn(
                                'size-4 transition-transform duration-300',
                                open && 'rotate-180'
                            )}
                            strokeWidth={1.75}
                        />
                    </button>
                </div>
            </div>
            <AnimatePresence initial={false}>
                {open && (
                    <motion.div
                        initial={{ opacity: 0, height: 0 }}
                        animate={{ opacity: 1, height: 'auto' }}
                        exit={{ opacity: 0, height: 0 }}
                        transition={{ duration: 0.2, ease: 'easeOut' }}
                        style={{ overflow: 'hidden' }}
                    >
                        <div className="border-t border-neutral-300 pt-4 mt-2 grid grid-cols-1 gap-4">
                            {variants
                                .slice(0, displayCount)
                                .map((variant, index) => (
                                    <div
                                        key={index}
                                        className="flex justify-between items-center pr-8"
                                    >
                                        <div className="flex flex-row items-center justify-start gap-2">
                                            <Link
                                                href={
                                                    'https://' + variant.domain
                                                }
                                                target="_blank"
                                                rel="noreferrer"
                                                className="font-normal"
                                            >
                                                {variant.domain}
                                            </Link>
                                            <span
                                                className={cn(
                                                    DomainStatusColor[
                                                        variant.status
                                                    ],
                                                    'text-neutral-800 font-semibold text-[0.4rem] border px-1 flex items-center h-[14px] rounded-xl'
                                                )}
                                            >
                                                {variant.status}
                                            </span>
                                            <div className="flex items-center gap-1">
                                                <button
                                                    className={cn(
                                                        'hover:cursor-pointer hover:scale-110 transition-all duration-300',
                                                        getVoteForDomain(
                                                            variant.domain
                                                        ) === 1 &&
                                                            'text-green-600'
                                                    )}
                                                    onClick={() =>
                                                        handleVote(
                                                            variant.domain,
                                                            1
                                                        )
                                                    }
                                                >
                                                    <ThumbsUp
                                                        className={cn(
                                                            'size-3',
                                                            getVoteForDomain(
                                                                variant.domain
                                                            ) === 1 &&
                                                                'text-green-600'
                                                        )}
                                                        strokeWidth={1.75}
                                                    />
                                                </button>
                                                <button
                                                    className={cn(
                                                        'hover:cursor-pointer hover:scale-110 transition-all duration-300',
                                                        getVoteForDomain(
                                                            variant.domain
                                                        ) === -1 &&
                                                            'text-red-600'
                                                    )}
                                                    onClick={() =>
                                                        handleVote(
                                                            variant.domain,
                                                            -1
                                                        )
                                                    }
                                                >
                                                    <ThumbsDown
                                                        className={cn(
                                                            'size-3',
                                                            getVoteForDomain(
                                                                variant.domain
                                                            ) === -1 &&
                                                                'text-red-600'
                                                        )}
                                                        strokeWidth={1.75}
                                                    />
                                                </button>
                                            </div>
                                        </div>
                                        <div className="flex gap-4 items-center justify-end">
                                            <button
                                                type="button"
                                                className={cn(
                                                    'hover:cursor-pointer hover:scale-110 transition-all duration-300',
                                                    isDomainFavorited(
                                                        variant.domain
                                                    ) && 'text-red-600',
                                                    !session?.user?.id &&
                                                        'opacity-50 cursor-not-allowed'
                                                )}
                                                onClick={(e) => {
                                                    e.preventDefault();
                                                    e.stopPropagation();

                                                    handleFavorite(
                                                        variant.domain
                                                    );
                                                }}
                                                disabled={!session?.user?.id}
                                            >
                                                <Heart
                                                    className={cn(
                                                        'size-4 pointer-events-none',
                                                        isDomainFavorited(
                                                            variant.domain
                                                        ) &&
                                                            'text-red-600 fill-red-600'
                                                    )}
                                                    strokeWidth={1.75}
                                                    fill={
                                                        isDomainFavorited(
                                                            variant.domain
                                                        )
                                                            ? 'currentColor'
                                                            : 'none'
                                                    }
                                                />
                                            </button>
                                            <button className="hover:cursor-pointer hover:scale-110 transition-all duration-300">
                                                <ShoppingCart
                                                    className="size-4"
                                                    strokeWidth={1.75}
                                                />
                                            </button>
                                        </div>
                                    </div>
                                ))}

                            {loading && variants.length === 0 ? (
                                <span className="flex items-center justify-center text-xs py-1 animate-pulse">
                                    Checking other top-level domains...
                                </span>
                            ) : (
                                <div className="w-full flex items-center justify-center pt-2">
                                    {canShowMoreLocal ? (
                                        <Button
                                            onClick={handleShowMore}
                                            size="sm"
                                        >
                                            Show more
                                        </Button>
                                    ) : canGenerateMore &&
                                      variants.length > 0 ? (
                                        <Button
                                            onClick={handleGenerateMore}
                                            size="sm"
                                        >
                                            Generate more
                                        </Button>
                                    ) : loading && variants.length > 0 ? (
                                        <span className="text-xs animate-pulse">
                                            Generating...
                                        </span>
                                    ) : !loading &&
                                      variants.length === 0 &&
                                      isStreamFinished ? (
                                        <span className="text-xs">
                                            No other TLDs found.
                                        </span>
                                    ) : null}
                                </div>
                            )}
                        </div>
                    </motion.div>
                )}
            </AnimatePresence>
        </Card>
    );
}

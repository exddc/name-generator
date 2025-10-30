'use client';

// Libraries
import React, { useEffect, useRef, useState } from 'react';
import { Domain, DomainStatus, DomainStatusColor } from '@/lib/types';
import { cn } from '@/lib/utils';

// Components
import Link from 'next/link';
import { ChevronDown, Heart, ShoppingCart } from 'lucide-react';
import { Card } from '@/components/ui/card';
import { Button } from '../ui/button';

// Constants
const DOMAIN_VARIANTS_URL = `${process.env.NEXT_PUBLIC_API_URL}/v1/domain/variants/stream`;

export default function DomainRow({ domain }: { domain: Domain }) {
    const [open, setOpen] = useState(false);
    const [loading, setLoading] = useState(false);
    const [variants, setVariants] = useState<Domain[]>([]);
    const [displayCount, setDisplayCount] = useState(5);
    const [fetchLimit, setFetchLimit] = useState(5);
    const [isStreamFinished, setIsStreamFinished] = useState(true);

    const abortControllerRef = useRef<AbortController | null>(null);

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
                </div>
                <div className="flex gap-4 items-center justify-end">
                    <button className="hover:cursor-pointer hover:scale-110 transition-all duration-300">
                        <Heart className="size-4" strokeWidth={1.75} />
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
            <div
                className={cn(
                    'overflow-hidden transition-all duration-300 ease-in-out',
                    open ? 'h-fit' : 'max-h-0'
                )}
            >
                <div className="border-t border-neutral-300 pt-4 mt-2 grid grid-cols-1 gap-4">
                    {variants.slice(0, displayCount).map((variant, index) => (
                        <div
                            key={index}
                            className="flex justify-between items-center pr-8"
                        >
                            <div className="flex flex-row items-center justify-start gap-2">
                                <Link
                                    href={'https://' + variant.domain}
                                    target="_blank"
                                    rel="noreferrer"
                                    className="font-normal"
                                >
                                    {variant.domain}
                                </Link>
                                <span
                                    className={cn(
                                        DomainStatusColor[variant.status],
                                        'text-neutral-800 font-semibold text-[0.4rem] border px-1 flex items-center h-[14px] rounded-xl'
                                    )}
                                >
                                    {variant.status}
                                </span>
                            </div>
                            <div className="flex gap-4 items-center justify-end">
                                <button className="hover:cursor-pointer hover:scale-110 transition-all duration-300">
                                    <Heart
                                        className="size-4"
                                        strokeWidth={1.75}
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

                    {open &&
                        (loading && variants.length === 0 ? (
                            <span className="flex items-center justify-center text-xs py-1 animate-pulse">
                                Checking other top-level domains...
                            </span>
                        ) : (
                            <div className="w-full flex items-center justify-center pt-2">
                                {canShowMoreLocal ? (
                                    <Button onClick={handleShowMore} size="sm">
                                        Show more
                                    </Button>
                                ) : canGenerateMore && variants.length > 0 ? (
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
                        ))}
                </div>
            </div>
        </Card>
    );
}

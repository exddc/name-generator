// Libraries
import { AnimatePresence, motion } from 'motion/react';
import Link from 'next/link';
import {
    Heart,
    ShoppingCart,
    Split,
    Globe,
    RefreshCw,
    ThumbsUp,
    ThumbsDown,
} from 'lucide-react';

// Components
import { Button } from '../ui/button';

// Utils
import { cn, getDomainRegistrarUrl } from '@/lib/utils';
import { Domain, DomainStatusColor } from '@/lib/types';

type DomainRowDropdownProps = {
    open: boolean;
    variants: Domain[];
    similarDomains: Domain[];
    loading: boolean;
    similarLoading: boolean;
    error: boolean;
    similarError: boolean;
    onRetryVariants: () => void;
    onRetrySimilar: () => void;
    onGenerateVariants: () => void;
    onGenerateSimilar: () => void;
    onVote: (domainName: string, vote: 1 | -1) => void;
    getVoteForDomain: (domainName: string) => 1 | -1 | undefined;
    onFavorite: (domain: string) => void;
    isDomainFavorited: (domainName: string) => boolean;
    hasSession: boolean;
};

export default function DomainRowDropdown({
    open,
    variants,
    similarDomains,
    loading,
    similarLoading,
    error,
    similarError,
    onRetryVariants,
    onRetrySimilar,
    onGenerateVariants,
    onGenerateSimilar,
    onVote,
    getVoteForDomain,
    onFavorite,
    isDomainFavorited,
    hasSession,
}: DomainRowDropdownProps) {
    return (
        <AnimatePresence initial={false}>
            {open && (
                <motion.div
                    initial={{ opacity: 0, height: 0 }}
                    animate={{ opacity: 1, height: 'auto' }}
                    exit={{ opacity: 0, height: 0 }}
                    transition={{ duration: 0.2, ease: 'easeOut' }}
                    style={{ overflow: 'hidden' }}
                >
                    <div className="border-t border-neutral-300 pt-4 mt-2 flex flex-col">
                        {/* Similar Domains Section */}
                        <div className="flex flex-col">
                            <div className="flex items-center justify-between border-b border-neutral-200 pb-2">
                                <div className="flex items-center gap-1.5 text-xs text-neutral-500 font-semibold">
                                    <Split className="size-3" />
                                    Similar Domains
                                </div>
                                {similarError ? (
                                    <Button
                                        size="sm"
                                        variant="ghost"
                                        className="h-6 text-xs gap-1 min-w-[80px] border border-transparent hover:border-neutral-300"
                                        onClick={onRetrySimilar}
                                    >
                                        <RefreshCw className="size-3" />
                                        Retry
                                    </Button>
                                ) : similarLoading ? (
                                    <span className="h-6 flex items-center text-xs text-neutral-400 animate-pulse">
                                        Generating similar domains...
                                    </span>
                                ) : (
                                    <Button
                                        onClick={onGenerateSimilar}
                                        size="sm"
                                        variant="ghost"
                                        className="h-6 text-xs min-w-[80px] border border-transparent hover:border-neutral-300"
                                    >
                                        {similarDomains.length === 0
                                            ? 'Generate Similar'
                                            : 'Generate More'}
                                    </Button>
                                )}
                            </div>
                            <div
                                className="max-h-[320px] overflow-y-scroll scrollbar-always pr-1 space-y-2"
                                style={{ scrollbarGutter: 'stable both-edges' }}
                            >
                                {similarDomains.map((similar) => (
                                    <div
                                        key={`similar-${similar.domain}`}
                                        className="flex justify-between items-center pr-8"
                                    >
                                        <div className="flex flex-row items-center justify-start gap-2">
                                            {similar.isNew && (
                                                <div className="h-1.5 w-1.5 min-h-[6px] min-w-[6px] rounded-full bg-sky-500 animate-pulse" />
                                            )}
                                            <Link
                                                href={
                                                    'https://' + similar.domain
                                                }
                                                target="_blank"
                                                rel="noreferrer"
                                                className="font-normal text-sm md:text-base"
                                            >
                                                {similar.domain}
                                            </Link>
                                            <span
                                                className={cn(
                                                    DomainStatusColor[
                                                        similar.status
                                                    ],
                                                    'text-neutral-800 font-semibold text-[0.4rem] border px-1 flex items-center h-[14px] rounded-xl'
                                                )}
                                            >
                                                {similar.status}
                                            </span>
                                            <div className="flex items-center gap-1">
                                                <button
                                                    className={cn(
                                                        'hover:cursor-pointer hover:scale-110 transition-all duration-300',
                                                        getVoteForDomain(
                                                            similar.domain
                                                        ) === 1 &&
                                                            'text-green-600'
                                                    )}
                                                    onClick={() =>
                                                        onVote(
                                                            similar.domain,
                                                            1
                                                        )
                                                    }
                                                >
                                                    <ThumbsUp
                                                        className={cn(
                                                            'size-3',
                                                            getVoteForDomain(
                                                                similar.domain
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
                                                            similar.domain
                                                        ) === -1 &&
                                                            'text-red-600'
                                                    )}
                                                    onClick={() =>
                                                        onVote(
                                                            similar.domain,
                                                            -1
                                                        )
                                                    }
                                                >
                                                    <ThumbsDown
                                                        className={cn(
                                                            'size-3',
                                                            getVoteForDomain(
                                                                similar.domain
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
                                                        similar.domain
                                                    ) && 'text-red-600',
                                                    !hasSession && 'opacity-50'
                                                )}
                                                onClick={(e) => {
                                                    e.preventDefault();
                                                    e.stopPropagation();
                                                    onFavorite(similar.domain);
                                                }}
                                            >
                                                <Heart
                                                    className={cn(
                                                        'size-4 pointer-events-none',
                                                        isDomainFavorited(
                                                            similar.domain
                                                        ) &&
                                                            'text-red-600 fill-red-600'
                                                    )}
                                                    strokeWidth={1.75}
                                                    fill={
                                                        isDomainFavorited(
                                                            similar.domain
                                                        )
                                                            ? 'currentColor'
                                                            : 'none'
                                                    }
                                                />
                                            </button>
                                            <Link
                                                className="hover:cursor-pointer hover:scale-110 transition-all duration-300"
                                                href={getDomainRegistrarUrl(
                                                    similar.domain
                                                )}
                                                target="_blank"
                                                rel="noreferrer"
                                            >
                                                <ShoppingCart
                                                    className="size-4"
                                                    strokeWidth={1.75}
                                                />
                                            </Link>
                                        </div>
                                    </div>
                                ))}
                            </div>
                        </div>

                        {/* Variants Section */}
                        <div className="flex flex-col">
                            <div className="flex items-center justify-between py-2 border-b border-neutral-200">
                                <div className="flex items-center gap-1.5 text-xs text-neutral-500 font-semibold">
                                    <Globe className="size-3" />
                                    Other TLDs
                                </div>
                                {error ? (
                                    <Button
                                        size="sm"
                                        variant="ghost"
                                        className="h-6 text-xs gap-1 min-w-[80px] border border-transparent hover:border-neutral-300"
                                        onClick={onRetryVariants}
                                    >
                                        <RefreshCw className="size-3" />
                                        Retry
                                    </Button>
                                ) : loading ? (
                                    <span className="h-6 flex items-center text-xs text-neutral-400 animate-pulse">
                                        Checking other TLDs...
                                    </span>
                                ) : (
                                    <Button
                                        onClick={onGenerateVariants}
                                        size="sm"
                                        variant="ghost"
                                        className="h-6 text-xs min-w-[80px] border border-transparent hover:border-neutral-300"
                                    >
                                        {variants.length === 0
                                            ? 'Check TLDs'
                                            : 'Check More'}
                                    </Button>
                                )}
                            </div>
                            <div
                                className="max-h-[320px] overflow-y-scroll scrollbar-always pr-1 space-y-2"
                                style={{ scrollbarGutter: 'stable both-edges' }}
                            >
                                {variants.map((variant) => (
                                    <div
                                        key={`variant-${variant.domain}`}
                                        className="flex justify-between items-center pr-8"
                                    >
                                        <div className="flex flex-row items-center justify-start gap-2">
                                            {variant.isNew && (
                                                <div className="h-1.5 w-1.5 min-h-[6px] min-w-[6px] rounded-full bg-sky-500 animate-pulse" />
                                            )}
                                            <Link
                                                href={
                                                    'https://' + variant.domain
                                                }
                                                target="_blank"
                                                rel="noreferrer"
                                                className="font-normal text-sm md:text-base"
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
                                                        onVote(
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
                                                        onVote(
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
                                                    !hasSession && 'opacity-50'
                                                )}
                                                onClick={(e) => {
                                                    e.preventDefault();
                                                    e.stopPropagation();
                                                    onFavorite(variant.domain);
                                                }}
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
                                            <Link
                                                className="hover:cursor-pointer hover:scale-110 transition-all duration-300"
                                                href={getDomainRegistrarUrl(
                                                    variant.domain
                                                )}
                                                target="_blank"
                                                rel="noreferrer"
                                            >
                                                <ShoppingCart
                                                    className="size-4"
                                                    strokeWidth={1.75}
                                                />
                                            </Link>
                                        </div>
                                    </div>
                                ))}
                            </div>
                        </div>
                    </div>
                </motion.div>
            )}
        </AnimatePresence>
    );
}

'use client';

// Libraries
import { AnimatePresence, motion } from 'motion/react';
import { ChevronDown } from 'lucide-react';

// Components
import { DomainRow } from '@/components/DomainGenerator';
import { Domain } from '@/lib/types';

// Props
type DomainSectionProps = {
    title: string;
    domains: Domain[];
    isOpen: boolean;
    onToggle: () => void;
    itemKeySuffix: string;
    onVote?: (domainName: string, vote: 1 | -1) => void;
    onFavorite?: (domainName: string, isFavorited: boolean) => void;
};

export default function DomainSection({
    title,
    domains,
    isOpen,
    onToggle,
    itemKeySuffix,
    onVote,
    onFavorite,
}: DomainSectionProps) {
    if (!domains.length) {
        return null;
    }

    return (
        <section className="space-y-2">
            <button
                type="button"
                className="cursor-pointer text-sm font-semibold ml-2 flex w-full items-center justify-between text-left text-neutral-800"
                onClick={onToggle}
                aria-expanded={isOpen}
            >
                <span>{title}</span>
                <motion.span
                    aria-hidden
                    animate={{ rotate: isOpen ? 0 : -90 }}
                    transition={{ duration: 0.2, ease: 'easeOut' }}
                    className="flex h-5 w-5 items-center justify-center text-neutral-500"
                >
                    <ChevronDown className="size-4" strokeWidth={1.75} />
                </motion.span>
            </button>
            <AnimatePresence initial={false}>
                {isOpen && (
                    <motion.div
                        key={`${itemKeySuffix}-content`}
                        initial={{ opacity: 0, height: 0 }}
                        animate={{ opacity: 1, height: 'auto' }}
                        exit={{ opacity: 0, height: 0 }}
                        transition={{ duration: 0.2, ease: 'easeOut' }}
                        style={{ overflow: 'hidden' }}
                    >
                        <div className="pt-2 space-y-2">
                            <AnimatePresence mode="popLayout">
                                {domains.map((domain) => (
                                    <motion.div
                                        key={`${domain.domain}-${itemKeySuffix}`}
                                        initial={{ opacity: 0, height: 0 }}
                                        animate={{ opacity: 1, height: 'auto' }}
                                        exit={{ opacity: 0, height: 0 }}
                                        transition={{
                                            duration: 0.2,
                                            ease: 'easeOut',
                                        }}
                                        style={{ overflow: 'hidden' }}
                                    >
                                        <DomainRow
                                            domain={domain}
                                            onVote={onVote}
                                            onFavorite={onFavorite}
                                        />
                                    </motion.div>
                                ))}
                            </AnimatePresence>
                        </div>
                    </motion.div>
                )}
            </AnimatePresence>
        </section>
    );
}

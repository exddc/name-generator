import * as React from 'react';
import { ChevronDown } from 'lucide-react';
import { motion, AnimatePresence } from 'motion/react';
import { cn } from '@/lib/utils';

interface CollapsibleProps {
    title: string;
    children: React.ReactNode;
    defaultOpen?: boolean;
    className?: string;
    count?: number;
}

export function Collapsible({
    title,
    children,
    defaultOpen = false,
    className,
    count,
}: CollapsibleProps) {
    const [isOpen, setIsOpen] = React.useState(defaultOpen);

    return (
        <div
            className={cn(
                'rounded-xl border border-border/50 bg-background/50',
                className
            )}
        >
            <button
                onClick={() => setIsOpen(!isOpen)}
                className="flex w-full items-center justify-between p-4 text-sm font-medium hover:bg-muted/50 transition-colors rounded-xl"
            >
                <div className="flex items-center gap-2">
                    <span>{title}</span>
                    {count !== undefined && (
                        <span className="px-2 py-0.5 rounded-full bg-muted text-xs text-muted-foreground">
                            {count}
                        </span>
                    )}
                </div>
                <motion.div
                    animate={{ rotate: isOpen ? 180 : 0 }}
                    transition={{ duration: 0.2 }}
                >
                    <ChevronDown className="h-4 w-4 text-muted-foreground" />
                </motion.div>
            </button>
            <AnimatePresence initial={false}>
                {isOpen && (
                    <motion.div
                        initial={{ height: 0, opacity: 0 }}
                        animate={{ height: 'auto', opacity: 1 }}
                        exit={{ height: 0, opacity: 0 }}
                        transition={{ duration: 0.2 }}
                        className="overflow-hidden"
                    >
                        <div className="p-4 pt-0 mt-2">{children}</div>
                    </motion.div>
                )}
            </AnimatePresence>
        </div>
    );
}

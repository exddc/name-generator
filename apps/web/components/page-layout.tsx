import { cn } from '@/lib/utils';
import { motion } from 'motion/react';

interface PageShellProps {
    children: React.ReactNode;
    className?: string;
}

export function PageShell({ children, className }: PageShellProps) {
    return (
        <div
            className={cn(
                'flex flex-col w-full items-center gap-8 md:gap-12 mt-6 md:mt-12 px-4 md:px-0 mb-24',
                className
            )}
        >
            {children}
        </div>
    );
}

interface PageHeaderProps {
    title: string;
    description?: string;
    children?: React.ReactNode;
    className?: string;
}

export function PageHeader({
    title,
    description,
    children,
    className,
}: PageHeaderProps) {
    return (
        <div
            className={cn(
                'w-full max-w-6xl xl:w-[1152px] flex flex-col gap-2',
                className
            )}
        >
            <div className="flex flex-col md:flex-row justify-between items-start md:items-center gap-4">
                <motion.div
                    initial={{ opacity: 0, y: 10 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ duration: 0.5 }}
                >
                    <h1 className="text-3xl font-heading font-semibold tracking-tight">
                        {title}
                    </h1>
                    {description && (
                        <p className="text-gray-600 text-base mt-1">
                            {description}
                        </p>
                    )}
                </motion.div>
                {children && (
                    <motion.div
                        initial={{ opacity: 0, x: 10 }}
                        animate={{ opacity: 1, x: 0 }}
                        transition={{ duration: 0.5, delay: 0.1 }}
                    >
                        {children}
                    </motion.div>
                )}
            </div>
        </div>
    );
}


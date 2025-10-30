import { cn } from '@/lib/utils';

function Card({
    children,
    className,
}: {
    children: React.ReactNode;
    className?: string;
}) {
    return (
        <div
            className={cn(
                'w-full bg-white p-5 rounded-2xl backdrop-blur-lg bg-opacity-40 border border-neutral-300 transition-all duration-500 flex',
                className
            )}
        >
            {children}
        </div>
    );
}

export { Card };

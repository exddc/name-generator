import { Button } from '@/components/ui/button';
import { cn } from '@/lib/utils';
import { ArrowRight } from 'lucide-react';

interface ButtonColorfulProps
    extends React.ButtonHTMLAttributes<HTMLButtonElement> {
    label?: string;
}

export function ButtonColorful({
    className,
    label = 'Explore Components',
    ...props
}: ButtonColorfulProps) {
    return (
        <Button
            className={cn(
                'relative h-10 px-4 ',
                'bg-zinc-900 dark:bg-zinc-100',
                'transition-all duration-200',
                'group',
                className
            )}
            {...props}
        >
            {/* Gradient background effect */}
            <div
                className={cn(
                    'absolute inset-0',
                    'bg-gradient-to-r from-indigo-500 via-purple-500 to-pink-500',
                    'opacity-20 group-hover:opacity-100',
                    'blur-lg transition-opacity duration-700'
                )}
            />

            {/* Content */}
            <div className="relative flex items-center justify-center gap-2">
                <span className="text-white dark:text-zinc-900">{label}</span>
                <ArrowRight className="w-3.5 h-3.5 text-white/90 dark:text-zinc-900/90" />
            </div>
        </Button>
    );
}

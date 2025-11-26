'use client';

import { useTheme } from 'next-themes';
import { Toaster as Sonner, toast } from 'sonner';

type ToasterProps = React.ComponentProps<typeof Sonner>;

const Toaster = ({ ...props }: ToasterProps) => {
    const { theme = 'system' } = useTheme();

    return (
        <Sonner
            theme={theme as ToasterProps['theme']}
            className="toaster group"
            toastOptions={{
                classNames: {
                    toast: 'group toast group-[.toaster]:bg-white group-[.toaster]:text-neutral-950 group-[.toaster]:border-neutral-200 group-[.toaster]:shadow-lg group-[.toaster]:rounded-xl',
                    description: 'group-[.toast]:text-neutral-500',
                    actionButton:
                        'group-[.toast]:bg-neutral-900 group-[.toast]:text-neutral-50',
                    cancelButton:
                        'group-[.toast]:bg-neutral-100 group-[.toast]:text-neutral-500',
                    error: 'group-[.toaster]:bg-red-50 group-[.toaster]:text-red-900 group-[.toaster]:border-red-200',
                    success:
                        'group-[.toaster]:bg-green-50 group-[.toaster]:text-green-900 group-[.toaster]:border-green-200',
                    warning:
                        'group-[.toaster]:bg-amber-50 group-[.toaster]:text-amber-900 group-[.toaster]:border-amber-200',
                    info: 'group-[.toaster]:bg-sky-50 group-[.toaster]:text-sky-900 group-[.toaster]:border-sky-200',
                },
            }}
            {...props}
        />
    );
};

export { Toaster, toast };

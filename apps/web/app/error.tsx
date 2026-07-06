'use client';

import { useEffect } from 'react';

export default function Error({
    error,
    reset,
}: {
    error: Error & { digest?: string };
    reset: () => void;
}) {
    useEffect(() => {
        console.error(error);
    }, [error]);

    return (
        <div className="flex flex-col items-center justify-center gap-6 py-32 text-center">
            <h2 className="text-3xl font-heading font-semibold tracking-tight">
                Something went wrong
            </h2>
            <p className="font-light text-base text-neutral-600 max-w-md text-balance">
                An unexpected error occurred while loading this page. You can try
                again.
            </p>
            <button
                onClick={reset}
                className="inline-flex items-center justify-center rounded-md bg-primary px-4 py-2 text-sm font-medium text-primary-foreground shadow transition-colors hover:bg-primary/90"
            >
                Try again
            </button>
        </div>
    );
}

'use client';

// global-error replaces the root layout when an error is thrown in the layout
// itself, so it renders its own <html>/<body> and imports the global styles.
import './globals.css';
import { useEffect } from 'react';

export default function GlobalError({
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
        <html lang="en">
            <body className="flex min-h-screen flex-col items-center justify-center gap-6 p-6 text-center font-sans antialiased">
                <h2 className="text-3xl font-semibold tracking-tight">
                    Something went wrong
                </h2>
                <p className="max-w-md text-balance font-light text-neutral-600">
                    The application failed to load. Please try again.
                </p>
                <button
                    onClick={reset}
                    className="inline-flex items-center justify-center rounded-md bg-neutral-900 px-4 py-2 text-sm font-medium text-white shadow transition-opacity hover:opacity-90"
                >
                    Try again
                </button>
            </body>
        </html>
    );
}

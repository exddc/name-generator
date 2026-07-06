import Link from 'next/link';

export default function NotFound() {
    return (
        <div className="flex flex-col items-center justify-center gap-6 py-32 text-center">
            <h2 className="text-3xl font-heading font-semibold tracking-tight">
                Page not found
            </h2>
            <p className="font-light text-base text-neutral-600 max-w-md text-balance">
                The page you&apos;re looking for doesn&apos;t exist or has moved.
            </p>
            <Link
                href="/"
                className="inline-flex items-center justify-center rounded-md bg-primary px-4 py-2 text-sm font-medium text-primary-foreground shadow transition-colors hover:bg-primary/90"
            >
                Back to home
            </Link>
        </div>
    );
}

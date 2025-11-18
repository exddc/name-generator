'use client';

// Libraries
import { useState } from 'react';
import { authClient } from '@/lib/auth-client';
import Link from 'next/link';

// Components
import { Card } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Button } from '@/components/ui/button';

export default function Login() {
    const [email, setEmail] = useState('');
    const [isLoading, setIsLoading] = useState(false);
    const [isSent, setIsSent] = useState(false);
    const [error, setError] = useState<string | null>(null);
    const isProduction = process.env.NODE_ENV === 'production';

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault();
        setIsLoading(true);
        setError(null);

        try {
            const result = await authClient.signIn.magicLink({
                email,
                callbackURL: '/',
            });

            console.log('Magic link request result:', result);
            setIsSent(true);
        } catch (err) {
            console.error('Magic link error:', err);
            const errorMessage =
                err instanceof Error
                    ? err.message
                    : 'Failed to send magic link. Please check the server console for details.';
            setError(errorMessage);
        } finally {
            setIsLoading(false);
        }
    };

    if (isSent) {
        return (
            <section className="flex min-h-[70vh] w-full items-center justify-center py-16">
                <Card className="w-full max-w-lg flex-col items-center gap-6 px-6 py-10 text-center md:px-12">
                    <span className="inline-flex h-14 w-14 items-center justify-center rounded-full bg-green-100 text-green-600">
                        <svg
                            className="h-7 w-7"
                            fill="none"
                            stroke="currentColor"
                            viewBox="0 0 24 24"
                        >
                            <path
                                strokeLinecap="round"
                                strokeLinejoin="round"
                                strokeWidth={2}
                                d="M5 13l4 4L19 7"
                            />
                        </svg>
                    </span>

                    <div className="space-y-2">
                        <h2 className="text-3xl font-semibold tracking-tight">
                            Magic link sent
                        </h2>
                        <p className="text-base text-gray-600 text-balance">
                            We just sent a secure login link to{' '}
                            <span className="font-medium text-gray-900">
                                {email}
                            </span>
                            . Follow it to finish signing in.
                        </p>
                    </div>

                    <div className="w-full">
                        {isProduction ? (
                            <div className="space-y-2 rounded-2xl border border-green-200 bg-green-50/80 p-4 text-left">
                                <p className="text-sm font-semibold text-green-900">
                                    Check your inbox
                                </p>
                                <p className="text-sm text-green-800">
                                    The link expires quickly, so open the email
                                    and click it within the next few minutes.
                                    Look in your spam or promotions folders if
                                    it doesn&apos;t arrive right away.
                                </p>
                            </div>
                        ) : (
                            <div className="space-y-2 rounded-2xl border border-blue-200 bg-blue-50/80 p-4 text-left">
                                <p className="text-sm font-semibold text-blue-900">
                                    Development mode
                                </p>
                                <p className="text-sm text-blue-800">
                                    Check the terminal running{' '}
                                    <code className="rounded bg-blue-100 px-1 py-0.5 text-xs font-semibold uppercase tracking-wide text-blue-900">
                                        bun dev
                                    </code>{' '}
                                    for the printed magic link URL. Copy and
                                    paste it into your browser to continue.
                                </p>
                            </div>
                        )}
                    </div>

                    <div className="flex w-full flex-col gap-3">
                        <Button
                            type="button"
                            className="w-full"
                            onClick={() => {
                                setIsSent(false);
                                setEmail('');
                            }}
                        >
                            Send another link
                        </Button>
                        <Link
                            href="/"
                            className="text-sm font-medium text-gray-600 transition hover:text-gray-900"
                        >
                            ← Back to home
                        </Link>
                    </div>
                </Card>
            </section>
        );
    }

    return (
        <section className="flex min-h-[70vh] w-full items-center justify-center py-16">
            <Card className="w-full max-w-lg flex-col gap-8 px-6 py-10 md:px-12">
                <div className="text-center">
                    <p className="text-sm font-medium uppercase tracking-wide text-blue-600">
                        Welcome back
                    </p>
                    <h1 className="mt-2 text-3xl font-semibold tracking-tight">
                        Sign in to continue
                    </h1>
                    <p className="mt-3 text-sm text-gray-600 text-balance">
                        Enter your email address and we&apos;ll send you a magic
                        link. No passwords, just one click.
                    </p>
                </div>

                <form
                    onSubmit={handleSubmit}
                    className="space-y-5 text-left"
                    noValidate
                >
                    <div className="space-y-2">
                        <label
                            htmlFor="email"
                            className="block text-sm font-medium text-gray-900"
                        >
                            Email address
                        </label>
                        <Input
                            id="email"
                            type="email"
                            value={email}
                            onChange={(e) => setEmail(e.target.value)}
                            required
                            disabled={isLoading}
                            placeholder="you@email.com"
                            className="h-12"
                        />
                    </div>

                    {error && (
                        <div className="rounded-2xl border border-red-200 bg-red-50/80 p-4">
                            <p className="text-sm text-red-800">{error}</p>
                        </div>
                    )}

                    <Button
                        type="submit"
                        disabled={isLoading || !email}
                        className="w-full"
                    >
                        {isLoading ? 'Sending...' : 'Send magic link'}
                    </Button>
                </form>

                <div className="text-center text-sm text-gray-500">
                    By continuing you agree to receive a one-time sign-in link
                    to the email above.
                </div>

                <div className="text-center">
                    <Link
                        href="/"
                        className="text-sm font-medium text-gray-600 transition hover:text-gray-900"
                    >
                        ← Back to home
                    </Link>
                </div>
            </Card>
        </section>
    );
}

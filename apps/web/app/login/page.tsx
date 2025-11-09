'use client';

// Libraries
import { useState } from 'react';
import { authClient } from '@/lib/auth-client';
import Link from 'next/link';
import { cn } from '@/lib/utils';

// Components
import { Card } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Button } from '@/components/ui/button';

export default function Login() {
    const [email, setEmail] = useState('');
    const [isLoading, setIsLoading] = useState(false);
    const [isSent, setIsSent] = useState(false);
    const [error, setError] = useState<string | null>(null);

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
            <div className="flex flex-col items-center justify-center w-full gap-8">
                <Card>
                    <div className="text-center">
                        <div className="mb-4">
                            <svg
                                className="mx-auto h-12 w-12 text-green-500"
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
                        </div>
                        <h2 className="text-2xl font-semibold mb-2">
                            Magic link generated
                        </h2>
                        <p className="text-gray-600 mb-4">
                            A magic link has been generated for{' '}
                            <strong>{email}</strong>.
                        </p>
                        <div className="bg-blue-50 border border-blue-200 rounded-lg p-4 mb-6">
                            <p className="text-sm text-blue-800">
                                <strong>🔍 Development Mode:</strong> Check your{' '}
                                <strong>server terminal/console</strong>
                                (where you ran{' '}
                                <code className="bg-blue-100 px-1 rounded">
                                    bun dev
                                </code>
                                ) to see the magic link URL. Copy it and open it
                                in your browser to sign in.
                            </p>
                            <p className="text-xs text-blue-700 mt-2">
                                Note: In production, this link would be sent via
                                email. The user account will be created
                                automatically when you click the magic link.
                            </p>
                        </div>
                        <button
                            onClick={() => {
                                setIsSent(false);
                                setEmail('');
                            }}
                            className={cn(
                                'inline-flex items-center justify-center gap-2 whitespace-nowrap rounded-md text-sm font-medium transition-colors focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring disabled:pointer-events-none disabled:opacity-50',
                                'bg-primary text-primary-foreground shadow hover:bg-primary/90',
                                'h-9 px-4 py-2',
                                'w-full'
                            )}
                        >
                            Send another link
                        </button>
                    </div>
                </Card>
            </div>
        );
    }

    return (
        <div className="flex flex-col items-center justify-center w-full -mt-64">
            <Card className="w-full max-w-md flex flex-col">
                <div className="mb-6">
                    <h1 className="text-3xl font-semibold tracking-tight mb-2">
                        Sign in
                    </h1>
                    <p className="text-gray-600 text-sm text-balance">
                        Enter your email address and we'll send you a link to
                        sign in.
                    </p>
                </div>

                <form onSubmit={handleSubmit} className="space-y-4">
                    <div>
                        <label
                            htmlFor="email"
                            className="block text-sm font-medium mb-2"
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
                            placeholder="your@email.com"
                        />
                    </div>

                    {error && (
                        <div className="p-3 rounded-md bg-red-50 border border-red-200">
                            <p className="text-sm text-red-800">{error}</p>
                        </div>
                    )}

                    <Button
                        type="submit"
                        disabled={isLoading || !email}
                        className="w-full"
                    >
                        {isLoading ? 'Sending...' : 'Send link'}
                    </Button>
                </form>

                <div className="mt-6 text-center">
                    <Link
                        href="/"
                        className="text-sm text-gray-600 hover:text-gray-900"
                    >
                        ← Back to home
                    </Link>
                </div>
            </Card>
        </div>
    );
}

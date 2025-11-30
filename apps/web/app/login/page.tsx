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
    const [useCode, setUseCode] = useState(false);
    const [otpCode, setOtpCode] = useState('');
    const [isVerifying, setIsVerifying] = useState(false);
    const isProduction = process.env.NODE_ENV === 'production';

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault();
        setIsLoading(true);
        setError(null);

        try {
            const result = await authClient.emailOtp.sendVerificationOtp({
                email,
                type: 'sign-in',
            });

            console.log('OTP request result:', result);
            setIsSent(true);
        } catch (err) {
            console.error('Login error:', err);
            const errorMessage =
                err instanceof Error
                    ? err.message
                    : 'Failed to send login credentials. Please check the server console for details.';
            setError(errorMessage);
        } finally {
            setIsLoading(false);
        }
    };

    const handleVerifyOTP = async (e: React.FormEvent) => {
        e.preventDefault();
        setIsVerifying(true);
        setError(null);

        try {
            const result = await authClient.signIn.emailOtp({
                email,
                otp: otpCode,
            });

            console.log('OTP verification result:', result);
        } catch (err) {
            console.error('OTP verification error:', err);
            const errorMessage =
                err instanceof Error
                    ? err.message
                    : 'Invalid code. Please try again.';
            setError(errorMessage);
        } finally {
            setIsVerifying(false);
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
                            Check your email
                        </h2>
                        <p className="text-base text-gray-600 text-balance">
                            We just sent a secure login link and a 6-digit code
                            to{' '}
                            <span className="font-medium text-gray-900">
                                {email}
                            </span>
                            . Choose how you'd like to sign in.
                        </p>
                    </div>

                    {!useCode ? (
                        <div className="w-full space-y-4">
                            {isProduction ? (
                                <div className="space-y-2 rounded-2xl border border-green-200 bg-green-50/80 p-4 text-left">
                                    <p className="text-sm font-semibold text-green-900">
                                        Check your inbox
                                    </p>
                                    <p className="text-sm text-green-800">
                                        The link expires quickly, so open the
                                        email and click it within the next few
                                        minutes. Look in your spam or promotions
                                        folders if it doesn&apos;t arrive right
                                        away.
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
                                        for the printed magic link URL and OTP
                                        code. Copy and paste the URL into your
                                        browser or use the code below.
                                    </p>
                                </div>
                            )}

                            <div className="flex items-center gap-4">
                                <div className="flex-1 border-t border-gray-200"></div>
                                <span className="text-sm text-gray-500">
                                    or
                                </span>
                                <div className="flex-1 border-t border-gray-200"></div>
                            </div>

                            <Button
                                type="button"
                                variant="outline"
                                className="w-full"
                                onClick={() => setUseCode(true)}
                            >
                                Enter 6-digit code instead
                            </Button>
                        </div>
                    ) : (
                        <form
                            onSubmit={handleVerifyOTP}
                            className="w-full space-y-4"
                        >
                            <div className="space-y-2">
                                <label
                                    htmlFor="otp-code"
                                    className="block text-sm font-medium text-gray-900"
                                >
                                    6-digit code
                                </label>
                                <Input
                                    id="otp-code"
                                    type="text"
                                    inputMode="numeric"
                                    pattern="[0-9]{6}"
                                    maxLength={6}
                                    value={otpCode}
                                    onChange={(e) => {
                                        const value = e.target.value
                                            .replace(/\D/g, '')
                                            .slice(0, 6);
                                        setOtpCode(value);
                                    }}
                                    required
                                    disabled={isVerifying}
                                    placeholder="000000"
                                    className="h-12 text-center text-2xl tracking-widest font-mono"
                                />
                                <p className="text-xs text-gray-500">
                                    Enter the 6-digit code sent to your email
                                </p>
                            </div>

                            {error && (
                                <div className="rounded-2xl border border-red-200 bg-red-50/80 p-4">
                                    <p className="text-sm text-red-800">
                                        {error}
                                    </p>
                                </div>
                            )}

                            <div className="flex gap-3">
                                <Button
                                    type="submit"
                                    disabled={
                                        isVerifying || otpCode.length !== 6
                                    }
                                    className="flex-1"
                                >
                                    {isVerifying
                                        ? 'Verifying...'
                                        : 'Verify code'}
                                </Button>
                                <Button
                                    type="button"
                                    variant="outline"
                                    onClick={() => {
                                        setUseCode(false);
                                        setOtpCode('');
                                        setError(null);
                                    }}
                                    disabled={isVerifying}
                                >
                                    Use link instead
                                </Button>
                            </div>
                        </form>
                    )}

                    <div className="flex w-full flex-col gap-3">
                        <Button
                            type="button"
                            variant="outline"
                            className="w-full"
                            onClick={() => {
                                setIsSent(false);
                                setEmail('');
                                setUseCode(false);
                                setOtpCode('');
                                setError(null);
                            }}
                        >
                            Send another code
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
            <Card className="w-full max-w-lg flex-col gap-8 px-6 py-10 md:px-12 border-neutral-200">
                <div className="text-center">
                    <h1 className="mt-2 text-3xl font-heading font-semibold tracking-tight">
                        Sign in to continue
                    </h1>
                    <p className="mt-3 text-sm text-gray-600 text-balance">
                        Enter your email address and we&apos;ll send you a magic
                        link and a 6-digit code. No passwords needed.
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
                        {isLoading ? 'Sending...' : 'Send login code'}
                    </Button>
                </form>

                <div className="text-center text-sm text-gray-500">
                    By continuing you agree to receive a one-time sign-in link
                    and code to the email above.
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

'use client';

// Libraries
import { useSession, signOut, authClient } from '@/lib/auth-client';
import Link from 'next/link';
import { cn } from '@/lib/utils';
import { useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';

// Components
import { Card } from '@/components/ui/card';
import HeroBackground from '@/components/HeroBackground';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';

export default function Profile() {
    const { data: session, isPending } = useSession();
    const router = useRouter();
    const [name, setName] = useState('');
    const [isSaving, setIsSaving] = useState(false);

    useEffect(() => {
        if (!isPending && !session?.user) {
            router.push('/login');
        }
    }, [session, isPending, router]);

    useEffect(() => {
        if (session?.user?.name) {
            setName(session.user.name);
        }
    }, [session?.user?.name]);

    if (isPending) {
        return (
            <div className="flex flex-col items-center justify-center min-h-[60vh] px-6">
                <div className="w-full max-w-md bg-white p-8 rounded-2xl backdrop-blur-lg bg-opacity-40 border border-neutral-200 shadow-lg">
                    <div className="text-center">
                        <p className="text-gray-600">Loading...</p>
                    </div>
                </div>
            </div>
        );
    }

    if (!session?.user) {
        return null;
    }

    const handleSignOut = async () => {
        await signOut();
        router.push('/');
    };

    const handleUpdateName = async () => {
        if (!name.trim() || name === session?.user?.name) {
            return;
        }

        setIsSaving(true);
        try {
            await authClient.updateUser({
                name: name.trim(),
            });
        } catch (error) {
            console.error('Failed to update name:', error);
            if (session?.user?.name) {
                setName(session.user.name);
            }
        } finally {
            setIsSaving(false);
        }
    };

    return (
        <main className="flex flex-col items-center justify-center max-w-6xl gap-64 mx-auto px-6 xl:px-0">
            <HeroBackground />
            <Card className="w-full max-w-md flex flex-col -mt-64">
                <div className="mb-6">
                    <h1 className="text-3xl font-semibold tracking-tight mb-2">
                        Profile
                    </h1>
                    <p className="text-gray-600">
                        Manage your account settings
                    </p>
                </div>

                <div className="space-y-4">
                    <div>
                        <label className="block text-sm font-medium mb-2">
                            Email
                        </label>
                        <div className="flex h-9 w-full rounded-md border border-input bg-white px-3 py-1 text-sm items-center">
                            {session.user.email}
                        </div>
                    </div>

                    <div>
                        <label className="block text-sm font-medium mb-2">
                            Name
                        </label>
                        <div className="flex gap-2">
                            <Input
                                type="text"
                                value={name}
                                onChange={(e) => setName(e.target.value)}
                                onBlur={handleUpdateName}
                                onKeyDown={(e) => {
                                    if (e.key === 'Enter') {
                                        e.currentTarget.blur();
                                    }
                                }}
                                disabled={isSaving}
                                className="flex-1"
                            />
                        </div>
                    </div>

                    <div className="pt-4 border-t flex flex-row items-center justify-between">
                        <Button variant="destructive" onClick={handleSignOut}>
                            Sign Out
                        </Button>

                        <Link
                            href="/"
                            className="text-sm text-gray-600 hover:text-gray-900"
                        >
                            ← Back to home
                        </Link>
                    </div>
                </div>
            </Card>
        </main>
    );
}

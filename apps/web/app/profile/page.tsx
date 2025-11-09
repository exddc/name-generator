'use client';

// Libraries
import { useSession, signOut, authClient } from '@/lib/auth-client';
import Link from 'next/link';
import { cn } from '@/lib/utils';
import { useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import { Domain, DomainStatus } from '@/lib/types';

// Components
import { Card } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { DomainRow } from '@/components/DomainGenerator';

const FAVORITE_API_URL = `${process.env.NEXT_PUBLIC_API_URL}/v1/user/favorite`;

export default function Profile() {
    const { data: session, isPending } = useSession();
    const router = useRouter();
    const [name, setName] = useState('');
    const [isSaving, setIsSaving] = useState(false);
    const [favorites, setFavorites] = useState<Domain[]>([]);
    const [isLoadingFavorites, setIsLoadingFavorites] = useState(false);

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

    useEffect(() => {
        const fetchFavorites = async () => {
            if (!session?.user?.id) {
                return;
            }

            setIsLoadingFavorites(true);
            try {
                const params = new URLSearchParams();
                params.append('user_id', session.user.id);
                params.append('page_size', '100'); // Fetch enough favorites

                const response = await fetch(
                    `${FAVORITE_API_URL}?${params.toString()}`
                );

                if (response.ok) {
                    const data = await response.json();
                    const domainObjects: Domain[] =
                        data.favorites?.map(
                            (favorite: {
                                domain: string;
                                tld: string;
                                status: DomainStatus;
                                rating?: number;
                                created_at: string;
                                updated_at: string;
                            }) => {
                                return {
                                    domain: favorite.domain,
                                    tld: favorite.tld,
                                    status: favorite.status,
                                    rating: favorite.rating,
                                    created_at: favorite.created_at,
                                    updated_at: favorite.updated_at,
                                };
                            }
                        ) || [];
                    setFavorites(domainObjects);
                }
            } catch (error) {
                console.error('Failed to fetch favorites:', error);
            } finally {
                setIsLoadingFavorites(false);
            }
        };

        fetchFavorites();
    }, [session?.user?.id]);

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
        <div className="flex flex-col items-center justify-center w-full gap-8">
            <div className="flex flex-col gap-8 w-full items-center justify-center">
                <div className="flex flex-row gap-8 w-full">
                    <Card className="w-full max-w-md flex flex-col mx-auto">
                        <div className="mb-6">
                            <h1 className="text-3xl font-semibold tracking-tight mb-2">
                                Profile
                            </h1>
                            <p className="text-gray-600">
                                Manage your account information
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
                                        onChange={(e) =>
                                            setName(e.target.value)
                                        }
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

                            <Button
                                variant="destructive"
                                onClick={handleSignOut}
                            >
                                Sign Out
                            </Button>
                        </div>
                    </Card>

                    <Card className="w-full max-w-md flex flex-col mx-auto">
                        <div className="mb-6">
                            <h2 className="text-3xl font-semibold tracking-tight mb-2">
                                Settings
                            </h2>
                            <p className="text-gray-600">
                                Manage your settings
                            </p>
                        </div>
                    </Card>
                </div>

                <Card className="w-full flex flex-col">
                    <div className="mb-6">
                        <h2 className="text-2xl font-semibold tracking-tight mb-2">
                            Favorites
                        </h2>
                        <p className="text-gray-600">Your favorited domains</p>
                    </div>

                    <div className="space-y-3">
                        {isLoadingFavorites ? (
                            <div className="text-center py-8">
                                <p className="text-gray-600">
                                    Loading favorites...
                                </p>
                            </div>
                        ) : favorites.length === 0 ? (
                            <div className="text-center py-8">
                                <p className="text-gray-600">
                                    No favorites yet. Start favoriting domains
                                    to see them here!
                                </p>
                            </div>
                        ) : (
                            favorites.map((domain) => (
                                <DomainRow
                                    key={domain.domain}
                                    domain={domain}
                                />
                            ))
                        )}
                    </div>
                </Card>
            </div>
        </div>
    );
}

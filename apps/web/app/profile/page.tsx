'use client';

// Libraries
import { useSession, signOut, authClient } from '@/lib/auth-client';
import { useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import { Domain, DomainStatus } from '@/lib/types';
import { toast } from '@/components/ui/sonner';

// Components
import { Card } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { DomainRow } from '@/components/DomainGenerator';
import { Skeleton } from '@/components/ui/skeleton';

import { PageShell, PageHeader } from '@/components/page-layout';

const FAVORITE_API_URL = `${process.env.NEXT_PUBLIC_API_URL}/v1/user/favorite`;

function FavoritesList({ userId }: { userId: string }) {
    const [favorites, setFavorites] = useState<Domain[]>([]);
    const [isLoading, setIsLoading] = useState(true);
    const [error, setError] = useState(false);

    useEffect(() => {
        const fetchFavorites = async () => {
            setIsLoading(true);
            setError(false);
            try {
                const params = new URLSearchParams();
                params.append('user_id', userId);
                params.append('page_size', '100');

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
                } else {
                    setError(true);
                }
            } catch (error) {
                console.warn('Failed to fetch favorites:', error);
                setError(true);
            } finally {
                setIsLoading(false);
            }
        };

        fetchFavorites();
    }, [userId]);

    if (isLoading) {
        return (
            <div className="space-y-3">
                {[1, 2, 3].map((i) => (
                    <Skeleton key={i} className="h-20 w-full" />
                ))}
            </div>
        );
    }

    if (error) {
        return (
            <div className="flex flex-col items-center justify-center py-8 text-center space-y-2">
                <p className="text-neutral-700 font-medium">
                    Unable to load favorites
                </p>
                <p className="text-neutral-600 text-sm">
                    There was a problem connecting to the server.
                </p>
            </div>
        );
    }

    if (favorites.length === 0) {
        return (
            <div className="text-center py-8">
                <p className="text-gray-600">
                    No favorites yet. Start favoriting domains to see them here!
                </p>
            </div>
        );
    }

    return (
        <div className="space-y-3">
            {favorites.map((domain) => (
                <DomainRow key={domain.domain} domain={domain} />
            ))}
        </div>
    );
}

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
            toast.success('Name updated successfully');
        } catch (error) {
            console.error('Failed to update name:', error);
            toast.error('Failed to update name. Please try again.');
            if (session?.user?.name) {
                setName(session.user.name);
            }
        } finally {
            setIsSaving(false);
        }
    };

    if (!isPending && !session?.user) {
        return null;
    }

    return (
        <PageShell>
            <PageHeader
                title="Account"
                description="Manage your profile and settings"
            />

            <div className="flex flex-col gap-8 w-full items-center justify-center max-w-6xl xl:w-[1152px]">
                <div className="flex flex-col md:flex-row gap-8 w-full">
                    <Card className="w-full flex flex-col mx-auto border-neutral-200">
                        <div className="mb-6">
                            <h2 className="text-xl font-heading font-semibold tracking-tight mb-2">
                                Profile
                            </h2>
                            <p className="text-gray-600 text-sm">
                                Manage your account information
                            </p>
                        </div>

                        <div className="space-y-4">
                            <div>
                                <label className="block text-sm font-medium mb-2">
                                    Email
                                </label>
                                <div className="flex h-9 w-full rounded-md border border-input bg-white px-3 py-1 text-sm items-center text-muted-foreground">
                                    {isPending ? (
                                        <Skeleton className="h-4 w-48" />
                                    ) : (
                                        session?.user?.email
                                    )}
                                </div>
                            </div>

                            <div>
                                <label className="block text-sm font-medium mb-2">
                                    Name
                                </label>
                                <div className="flex gap-2">
                                    {isPending ? (
                                        <Skeleton className="h-10 w-full" />
                                    ) : (
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
                                    )}
                                </div>
                            </div>

                            <Button
                                variant="destructive"
                                onClick={handleSignOut}
                                disabled={isPending}
                            >
                                Sign Out
                            </Button>
                        </div>
                    </Card>

                    <Card className="w-full flex flex-col mx-auto border-neutral-200">
                        <div className="mb-6">
                            <h2 className="text-xl font-heading font-semibold tracking-tight mb-2">
                                Settings
                            </h2>
                            <p className="text-gray-600 text-sm">
                                Manage your settings
                            </p>
                        </div>
                    </Card>
                </div>

                <Card className="w-full flex flex-col border-neutral-200">
                    <div className="mb-6">
                        <h2 className="text-xl font-heading font-semibold tracking-tight mb-2">
                            Favorites
                        </h2>
                        <p className="text-gray-600 text-sm">
                            Your favorited domains
                        </p>
                    </div>

                    {isPending ? (
                        <div className="space-y-3">
                            {[1, 2, 3].map((i) => (
                                <Skeleton key={i} className="h-20 w-full" />
                            ))}
                        </div>
                    ) : (
                        <FavoritesList userId={session!.user.id} />
                    )}
                </Card>
            </div>
        </PageShell>
    );
}

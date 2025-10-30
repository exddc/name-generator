'use client';

import { useSession, signOut } from '@/lib/auth-client';
import Link from 'next/link';
import { cn } from '@/lib/utils';
import { useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';

export default function Dashboard() {
    const { data: session, isPending } = useSession();
    const router = useRouter();
    const [isCheckingAccess, setIsCheckingAccess] = useState(true);

    useEffect(() => {
        if (!isPending && !session?.user) {
            router.push('/login');
            return;
        }

        if (session?.user) {
            const userRole = session.user.role;
            const isAdmin =
                userRole === 'admin' ||
                (typeof userRole === 'string' && userRole.includes('admin')) ||
                (Array.isArray(userRole) && userRole.includes('admin'));

            if (!isAdmin) {
                router.push('/');
                return;
            }

            setIsCheckingAccess(false);
        }
    }, [session, isPending, router]);

    if (isPending || isCheckingAccess) {
        return (
            <div className="flex flex-col items-center justify-center min-h-[60vh] px-6">
                <div className="w-full max-w-4xl bg-white p-8 rounded-2xl backdrop-blur-lg bg-opacity-40 border border-neutral-200 shadow-lg">
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

    return (
        <div className="flex flex-col items-center justify-center min-h-[60vh] px-6">
            <div className="w-full max-w-4xl bg-white p-8 rounded-2xl backdrop-blur-lg bg-opacity-40 border border-neutral-200 shadow-lg">
                <div className="mb-6">
                    <h1 className="text-3xl font-semibold tracking-tight mb-2">
                        Admin Dashboard
                    </h1>
                    <p className="text-gray-600">
                        Welcome to the admin dashboard. This page is only
                        accessible to administrators.
                    </p>
                </div>

                <div className="space-y-6">
                    <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
                        <h2 className="text-lg font-semibold mb-2 text-blue-900">
                            Dashboard Overview
                        </h2>
                        <p className="text-sm text-blue-800">
                            This is a skeleton dashboard page. You can add admin
                            features here such as:
                        </p>
                        <ul className="list-disc list-inside mt-2 text-sm text-blue-800 space-y-1">
                            <li>User management</li>
                            <li>System statistics</li>
                            <li>Domain analytics</li>
                            <li>Configuration settings</li>
                        </ul>
                    </div>

                    <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                        <div className="border border-neutral-200 rounded-lg p-4">
                            <h3 className="font-semibold mb-2">
                                User Management
                            </h3>
                            <p className="text-sm text-gray-600">
                                Manage users, roles, and permissions
                            </p>
                        </div>

                        <div className="border border-neutral-200 rounded-lg p-4">
                            <h3 className="font-semibold mb-2">Analytics</h3>
                            <p className="text-sm text-gray-600">
                                View system metrics and usage statistics
                            </p>
                        </div>

                        <div className="border border-neutral-200 rounded-lg p-4">
                            <h3 className="font-semibold mb-2">Settings</h3>
                            <p className="text-sm text-gray-600">
                                Configure application settings
                            </p>
                        </div>

                        <div className="border border-neutral-200 rounded-lg p-4">
                            <h3 className="font-semibold mb-2">Reports</h3>
                            <p className="text-sm text-gray-600">
                                Generate and view reports
                            </p>
                        </div>
                    </div>

                    <div className="pt-4 border-t">
                        <div className="flex gap-4">
                            <Link
                                href="/"
                                className={cn(
                                    'inline-flex items-center justify-center gap-2 whitespace-nowrap rounded-md text-sm font-medium transition-colors focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring disabled:pointer-events-none disabled:opacity-50',
                                    'bg-primary text-primary-foreground shadow hover:bg-primary/90',
                                    'h-9 px-4 py-2'
                                )}
                            >
                                Back to Home
                            </Link>
                            <Link
                                href="/profile"
                                className={cn(
                                    'inline-flex items-center justify-center gap-2 whitespace-nowrap rounded-md text-sm font-medium transition-colors focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring disabled:pointer-events-none disabled:opacity-50',
                                    'border border-input bg-background shadow-sm hover:bg-accent hover:text-accent-foreground',
                                    'h-9 px-4 py-2'
                                )}
                            >
                                View Profile
                            </Link>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    );
}

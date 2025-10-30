'use client';

// Libraries
import { useEffect, useState } from 'react';
import Link from 'next/link';
import { cn } from '@/lib/utils';
import { useSession } from '@/lib/auth-client';

// Components
import {
    NavigationMenu,
    NavigationMenuItem,
    NavigationMenuLink,
    NavigationMenuList,
    navigationMenuTriggerStyle,
} from '@/components/ui/navigation-menu';

export default function Header() {
    const [showBorder, setShowBorder] = useState(false);
    const { data: session } = useSession();

    useEffect(() => {
        function handleScroll() {
            if (window.scrollY > 80) {
                setShowBorder(true);
            } else {
                setShowBorder(false);
            }
        }

        window.addEventListener('scroll', handleScroll);

        return () => {
            window.removeEventListener('scroll', handleScroll);
        };
    }, []);

    return (
        <header className="sticky top-0 z-50">
            <div
                className={cn(
                    `mx-auto w-full py-5 backdrop-blur-sm bg-opacity-60 transition-all duration-700 border-b`,
                    showBorder
                        ? ' border-neutral-200 bg-white'
                        : ' border-transparent'
                )}
            >
                <div className="max-w-7xl mx-auto w-full flex flex-row justify-between">
                    <Link
                        href="/"
                        className="text-lg font-bold justify-center items-center flex"
                    >
                        Domain Generator
                    </Link>

                    <NavigationMenu>
                        <NavigationMenuList>
                            <NavigationMenuItem>
                                <NavigationMenuLink
                                    asChild
                                    className={navigationMenuTriggerStyle()}
                                >
                                    <Link href="/top-domains">
                                        Top Rated Domains
                                    </Link>
                                </NavigationMenuLink>
                            </NavigationMenuItem>
                            <NavigationMenuItem>
                                <NavigationMenuLink
                                    asChild
                                    className={navigationMenuTriggerStyle()}
                                >
                                    {session?.user ? (
                                        <Link href="/profile">Profile</Link>
                                    ) : (
                                        <Link href="/login">Login</Link>
                                    )}
                                </NavigationMenuLink>
                            </NavigationMenuItem>
                        </NavigationMenuList>
                    </NavigationMenu>
                </div>
            </div>
        </header>
    );
}

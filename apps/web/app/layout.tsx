// Libraries
import type { Metadata } from 'next';
import PlausibleProvider from 'next-plausible';

// Components
import './globals.css';
import Header from '@/components/Header';
import Footer from '@/components/Footer';
import { Public_Sans, Manrope } from 'next/font/google';
import { Toaster } from '@/components/ui/sonner';

const publicSans = Public_Sans({
    variable: '--font-heading',
    subsets: ['latin'],
});

const manrope = Manrope({
    variable: '--font-sans',
    subsets: ['latin'],
});

export const metadata: Metadata = {
    title: 'Domain Generator',
    description:
        'Generate domain names for you business, app, or project that are guaranteed available to register',
    icons: {
        icon: '/icon.png',
    },
    openGraph: {
        title: 'Domain Generator',
        description:
            'Generate domain names for you business, app, or project that are guaranteed available to register',
        url: 'https://domain-generator.timoweiss.me',
        type: 'website',
        images: [
            {
                url: 'https://domain-generator.timoweiss.me/og-image.jpg',
                width: 1200,
                height: 630,
                alt: 'Domain Generator',
            },
        ],
    },
    twitter: {
        title: 'Domain Generator',
        description:
            'Generate domain names for you business, app, or project that are guaranteed available to register',
        images: ['https://domain-generator.timoweiss.me/og-image.jpg'],
        card: 'summary_large_image',
        creator: '@timooweiss',
    },
};

export default function RootLayout({
    children,
}: Readonly<{
    children: React.ReactNode;
}>) {
    return (
        <html lang="en" className="w-full h-full">
            <body
                className={`${publicSans.variable} ${manrope.variable} antialiased flex flex-col w-full min-h-screen font-sans`}
            >
                <PlausibleProvider domain="name-generator.timoweiss.me">
                    <div className="fixed inset-0 flex blur-[130px] z-0 justify-center items-center pointer-events-none overflow-hidden">
                        <div
                            className="animate-[spin_6s_linear_infinite]"
                            style={{
                                background:
                                    'conic-gradient(from 90deg at 50% 50%, #e59999 0%, #9683dd 100%)',
                                width: '400px',
                                height: '300px',
                                marginLeft: '0',
                            }}
                        ></div>
                        <div
                            className="animate-[spin_8s_linear_infinite]"
                            style={{
                                background:
                                    'conic-gradient(from 90deg at 50% 50%, #8fdadb 0%, #3957c0 100%)',
                                width: '400px',
                                height: '300px',
                                marginLeft: '20px',
                            }}
                        ></div>
                    </div>
                    <Header />
                    <main className="flex flex-col items-center max-w-6xl mx-auto px-4 xl:px-0 w-full relative z-10">
                        {children}
                    </main>
                    <Footer />
                </PlausibleProvider>
                <Toaster position="bottom-right" richColors closeButton />
            </body>
        </html>
    );
}

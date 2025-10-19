// Libraries
import type { Metadata } from 'next';
import { Inter } from 'next/font/google';

// Components
import './globals.css';
import Header from '@/components/Header';
import Footer from '@/components/Footer';

const interSans = Inter({
    variable: '--font-inter-sans',
    subsets: ['latin'],
});

export const metadata: Metadata = {
    title: 'Domain Generator',
    description:
        'Get domain options based on your idea that are available to register',
};

export default function RootLayout({
    children,
}: Readonly<{
    children: React.ReactNode;
}>) {
    return (
        <html lang="en" className="w-full h-screen">
            <body className={`${interSans.variable} antialiased flex flex-col`}>
                <Header />
                {children}
                <Footer />
            </body>
        </html>
    );
}

import type { Metadata } from 'next';
import Script from 'next/script';
import { Inter, Newsreader } from 'next/font/google';
import './globals.css';
import Header from '@/components/Header';
import Footer from '@/components/Footer';

const interSans = Inter({
    variable: '--font-inter-sans',
    subsets: ['latin'],
});

const newsreaderSerif = Newsreader({
    variable: '--font-newsreader-serif',
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
            <body
                className={`${interSans.variable} ${newsreaderSerif.variable} antialiased flex flex-col`}
            >
                <Header />
                {children}
                <Footer />
            </body>
            <Script
                defer
                data-domain="domain-generator.timoweiss.me"
                src="https://plausible.io/js/script.js"
            ></Script>
        </html>
    );
}

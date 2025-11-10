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
        <html lang="en" className="w-full h-full">
            <body
                className={`${interSans.variable} antialiased flex flex-col w-full min-h-screen`}
            >
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
            </body>
        </html>
    );
}

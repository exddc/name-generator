// Libraries
import React from 'react';
import {
    exampleDomains,
    exampleRegisteredDomains,
    faqQuestions,
} from '@/lib/marketing';
import { cn } from '@/lib/utils';

// Components
import Typewriter from '@/components/ui/typewriter';
import { FaqSection } from '@/components/ui/faq';
import ClientTweetCard from '@/components/ui/client-tweet-card';
import Link from 'next/link';
import Hero from '@/components/Hero';
import { DomainRow } from '@/components/DomainGenerator';

type HomeProps = {
    searchParams: { search?: string };
};

export default function Home({ searchParams }: HomeProps) {
    const searchQuery = searchParams?.search || '';

    return (
        <div className="flex flex-col items-center justify-center w-full gap-64">
            <Hero initialSearch={searchQuery} />

            <div
                id="get-many-suggestions"
                className="w-full flex align-middle justify-center gap-12 z-10"
            >
                <div className="w-full flex flex-col gap-4 text-left mt-20">
                    <h3 className="text-3xl font-semibold tracking-tight flex flex-col">
                        <span>Get useful suggestions</span>
                        <span>and iterations for your idea</span>
                    </h3>
                    <p className="font-light text-balance text-lg">
                        Finding a great domain name is the first step in
                        bringing your business, app, or project to the web.
                        <br />
                        Our AI takes your description and in seconds provides
                        available domain names that you can register or iterate
                        on.
                    </p>
                </div>
                <div className="w-full space-y-4 mt-6 bg-white p-5 rounded-2xl backdrop-blur-lg bg-opacity-40 border border-neutral-200">
                    <details open>
                        <summary className="cursor-pointer text-sm font-semibold mb-2 ml-2">
                            Available Domains ({exampleDomains.length})
                        </summary>
                        <div className="mt-2 space-y-2">
                            {exampleDomains.map((domain) => (
                                <DomainRow
                                    domain={domain}
                                    key={domain.domain + '-example-domain'}
                                />
                            ))}
                        </div>
                    </details>

                    <details>
                        <summary className="cursor-pointer text-sm font-semibold mb-2 ml-2">
                            Registered Domains (
                            {exampleRegisteredDomains.length})
                        </summary>
                        <div className="mt-2 space-y-2">
                            {exampleRegisteredDomains.map((domain) => (
                                <DomainRow
                                    domain={domain}
                                    key={
                                        domain.domain +
                                        '-example-registered-domain'
                                    }
                                />
                            ))}
                        </div>
                    </details>
                </div>
            </div>

            <div
                id="explain-your-idea"
                className="w-full flexalign-middle flex flex-row justify-center transition-all duration-300 gap-12 z-10 items-center"
            >
                <div className="relative overflow-hidden rounded-xl group w-full">
                    <div className="w-full mt-6 bg-white p-5 rounded-2xl backdrop-blur-lg bg-opacity-40 border border-neutral-200 max-w-lg h-[200px] flex flex-col justify-between">
                        <div className="flex border border-[#D9D9D9] px-4 py-2 text-sm justify-between rounded-xl bg-white w-full">
                            <Typewriter
                                text={[
                                    'Local woodworkingshop speacializing in custom furniture in Munich, Germany',
                                    'A new social media app for sharing photos and videos with only your closest friends',
                                    'A subscription service for monthly deliveries of high-quality coffee beans from around the world to your doorstep',
                                ]}
                                speed={50}
                                loop={true}
                                waitTime={5000}
                                initialDelay={2000}
                            />
                            <button
                                className="pl-4 pr-2 border-l border-[#D9D9D9] bg-transparent"
                                disabled={true}
                            >
                                Go
                            </button>
                        </div>
                        <div className="w-full flex items-start justify-center -mt-2 h-[60px]">
                            <span className="text-xs text-gray-600 leading-none animate-pulse">
                                Generating suggestions...
                            </span>
                        </div>
                    </div>
                </div>
                <div className="w-full flex flex-col gap-4 text-right">
                    <h3 className="text-3xl font-semibold tracking-tight flex flex-col">
                        Describe what you&apos;re creating
                    </h3>
                    <p className="font-light text-balance text-lg">
                        Give a short description of your app, service, or
                        company idea. You will get at least 5 available domain
                        names that you can use.
                    </p>
                </div>
            </div>
            <div
                id="how-it-started"
                className="w-full flex align-middle justify-center gap-12 px-6 2xl:px-0 z-10 items-center"
            >
                <div className="w-full max-w-2xl flex flex-col gap-4 text-left">
                    <h3 className="text-3xl font-semibold tracking-tight flex flex-col">
                        How it started
                    </h3>
                    <p className="font-light text-balance text-lg">
                        I just wanted a good domain for another project I was
                        working on. After trying a few domain generators that
                        were all slow and didn&apos;t give me the results I
                        wanted, I decided to build my own. It&apos;s fast,
                        simple, and gives me the results I need.
                    </p>
                </div>
                <div className="max-w-sm h-fit">
                    <ClientTweetCard id="1867792841566826710" />
                </div>
            </div>

            <div
                id="top-domains"
                className="w-full flex align-middle justify-center gap-12 px-6 2xl:px-0 z-10 items-center"
            >
                <div className="w-full flex flex-col gap-4 text-center">
                    <h2 className="text-3xl font-semibold tracking-tight flex flex-col">
                        Explore and get Inspired by
                        <br />
                        the Top Rated Domains that are still available
                    </h2>
                    <p className="font-light text-balance text-lg">
                        Discover the top-rated domain names that are still
                        available to register.
                        <br />
                        Get inspired by the creativity of others and find a
                        domain that fits your brand and vision.
                    </p>
                    <Link
                        href="/top-domains"
                        className={cn(
                            'inline-flex items-center justify-center gap-2 whitespace-nowrap rounded-md text-sm font-medium transition-colors focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring disabled:pointer-events-none disabled:opacity-50 [&_svg]:pointer-events-none [&_svg]:size-4 [&_svg]:shrink-0',
                            'bg-primary text-primary-foreground shadow hover:bg-primary/90',
                            'h-9 px-4 py-2',
                            'w-fit mx-auto mt-6'
                        )}
                    >
                        View all Top Domains
                    </Link>
                </div>
            </div>

            <div
                id="faq"
                className="w-full flex z-10 align-middle justify-center px-6 2xl:px-0 items-center mb-64"
            >
                <FaqSection
                    title="Frequently Asked Questions"
                    description="Everything you need to know about domains"
                    items={faqQuestions}
                    className="w-full"
                />
            </div>

            <div
                id="get-started"
                className="w-full flex align-middle justify-center gap-12 px-6 2xl:px-0 z-10 items-center"
            >
                <div className="w-full flex flex-col gap-4 text-center">
                    <h2 className="text-3xl font-semibold tracking-tight flex flex-col">
                        Get the best fitting domain for your idea
                    </h2>
                    <p className="font-light text-balance text-lg">
                        Get yourself at least 5 available domain names that you
                        can use right now.
                    </p>
                    <Link
                        href="#"
                        className={cn(
                            'inline-flex items-center justify-center gap-2 whitespace-nowrap rounded-md text-sm font-medium transition-colors focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring disabled:pointer-events-none disabled:opacity-50 [&_svg]:pointer-events-none [&_svg]:size-4 [&_svg]:shrink-0',
                            'bg-primary text-primary-foreground shadow hover:bg-primary/90',
                            'h-9 px-4 py-2',
                            'w-fit mx-auto mt-6'
                        )}
                    >
                        Generate Domains
                    </Link>
                </div>
            </div>
        </div>
    );
}

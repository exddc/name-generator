'use client';

// Libraries
import React, { useState } from 'react';
import { DomainData } from '@/lib/types';
import {
    exampleDomains,
    exampleRegisteredDomains,
    faqQuestions,
} from '@/lib/marketing';

// Components
import Typewriter from '@/components/ui/typewriter';
import { FaqSection } from '@/components/ui/faq';
import ClientTweetCard from '@/components/ui/client-tweet-card';
import { handleDomainFeedback, DomainFeedback, cn } from '@/lib/utils';
import HeroBackground from '@/components/HeroBackground';
import Link from 'next/link';

// Constants
const NEXT_PUBLIC_API_URL = process.env.NEXT_PUBLIC_API_URL;
const NEXT_PUBLIC_SUGGEST_ENDPOINT = process.env.NEXT_PUBLIC_SUGGEST_ENDPOINT;

export default function Home() {
    const [userInput, setUserInput] = useState('');
    const [domains, setDomains] = useState<DomainData[]>([]);
    const [errorMsg, setErrorMsg] = useState<string | null>(null);
    const [isLoading, setIsLoading] = useState(false);
    const [textAreaRows, setTextAreaRows] = useState(1);
    const [domainFeedback, setDomainFeedback] = useState<DomainFeedback>({});

    const handleSuggestStream = (e: React.FormEvent) => {
        e.preventDefault();
        setIsLoading(true);
        setDomains([]);
        setDomainFeedback({});
        setErrorMsg(null);

        const url = `${NEXT_PUBLIC_API_URL}/${NEXT_PUBLIC_SUGGEST_ENDPOINT}?query=${encodeURIComponent(
            userInput
        )}`;

        const evtSource = new EventSource(url);

        evtSource.onopen = () => {
            console.log('SSE connection opened.');
        };

        evtSource.onerror = (err) => {
            console.error('SSE onerror triggered:', err);
            setErrorMsg(
                'A network or server error occurred while streaming data.'
            );
            setIsLoading(false);
            evtSource.close();
        };

        evtSource.onmessage = (e) => {
            console.log('Generic message:', e.data);
        };

        evtSource.addEventListener('domain_suggestion', (e: MessageEvent) => {
            try {
                const dataObj = JSON.parse(e.data) as DomainData;
                setDomains((prev) => [...prev, dataObj]);
            } catch (parseErr) {
                console.error(
                    'Error parsing domain_suggestion data:',
                    parseErr
                );
            }
        });

        evtSource.addEventListener('error', () => {
            console.error('SSE error event');
            setErrorMsg('Unknown error occurred.');
        });

        evtSource.addEventListener('done', (e: MessageEvent) => {
            console.log('SSE done event:', e.data);
            setIsLoading(false);
            evtSource.close();
        });
    };

    const freeDomains = domains.filter((d) => d.status === 'free');
    const registeredDomains = domains.filter((d) => d.status === 'registered');
    const unknownDomains = domains.filter(
        (d) => d.status !== 'free' && d.status !== 'registered'
    );

    const hasAnyDomains =
        freeDomains.length > 0 ||
        registeredDomains.length > 0 ||
        unknownDomains.length > 0;

    function renderDomainRow(item: DomainData, index: number) {
        const feedback = domainFeedback[item.domain]; // Number (1-10) or undefined

        return (
            <li
                key={index}
                className="flex border border-[#D9D9D9] px-4 py-2 rounded-xl text-sm justify-between bg-white"
            >
                <a
                    href={'https://' + item.domain}
                    target="_blank"
                    rel="noreferrer"
                >
                    {item.domain}
                </a>
                <div className="flex gap-4 items-center">
                    <p
                        className={
                            (item.status === 'free'
                                ? 'bg-green-500/30 border-green-700'
                                : item.status === 'registered'
                                ? 'bg-red-500/30 border-red-700'
                                : 'bg-yellow-500/30 border-yellow-700') +
                            ' text-black font-semibold text-[0.65rem] border px-2 flex items-center h-[18px] rounded-xl'
                        }
                    >
                        {item.status === 'free'
                            ? 'Available'
                            : item.status === 'registered'
                            ? 'Registered'
                            : 'Unknown'}
                    </p>
                    <div className="flex items-end gap-1">
                        {/* Label for 1 */}
                        <span className="text-xs text-gray-600 leading-none">
                            1
                        </span>
                        {/* Vertical rating bars */}
                        <div className="flex gap-[2px] items-end">
                            {Array.from({ length: 10 }, (_, i) => i + 1).map(
                                (rating) => (
                                    <div
                                        key={rating}
                                        className={
                                            'w-1 cursor-pointer transition-all duration-200 ' +
                                            (feedback === rating
                                                ? 'h-4 bg-blue-500'
                                                : 'h-2 bg-gray-400 hover:h-3 hover:bg-gray-500')
                                        }
                                        onClick={() => {
                                            handleDomainFeedback(
                                                item.domain,
                                                rating,
                                                setDomainFeedback
                                            );
                                        }}
                                    />
                                )
                            )}
                        </div>
                        {/* Label for 10 */}
                        <span className="text-xs text-gray-600 leading-none">
                            10
                        </span>
                    </div>
                </div>
            </li>
        );
    }

    return (
        <main className="flex flex-col items-center justify-center max-w-6xl gap-64 mx-auto px-6 xl:px-0">
            <HeroBackground />
            <div
                id="hero-domain-generator"
                className="w-full flex flex-col items-center justify-center"
            >
                <div
                    id="hero-content"
                    className={
                        'w-full max-w-3xl flex flex-col gap-2 items-center transition-all duration-1000 z-10 text-center' +
                        (hasAnyDomains ? ' -mt-[450px]' : ' -mt-[200px]')
                    }
                >
                    <h1 className="text-5xl font-bold flex flex-col tracking-tighter">
                        <span>Generate domain names</span>
                        <span>that are guaranteed available</span>
                    </h1>
                    <p className=" font-light text-balance text-lg tracking-tight">
                        Skip the guesswork and go straight to securing a name
                        that fits your brand and vision
                    </p>
                </div>

                <div
                    id="domain-generator-form"
                    className="w-full max-w-2xl space-y-4 mt-6 bg-white p-5 rounded-2xl backdrop-blur-lg bg-opacity-40 border border-neutral-200"
                >
                    <div className="relative overflow-hidden rounded-xl focus-within:ring-1 focus-within:ring-neutral-300">
                        <form
                            onSubmit={handleSuggestStream}
                            className="flex border border-[#D9D9D9] px-4 py-3 text-base justify-between rounded-xl bg-white"
                        >
                            <textarea
                                placeholder="Describe your app, service, or company idea..."
                                value={userInput}
                                onChange={(e) => {
                                    setUserInput(e.target.value);
                                    setTextAreaRows(
                                        Math.min(
                                            Math.max(
                                                1,
                                                e.target.value.length / 50 + 1
                                            ),
                                            10
                                        )
                                    );
                                }}
                                className="w-full outline-none bg-transparent pr-4"
                                rows={textAreaRows}
                                style={{ resize: 'none' }}
                                onKeyDown={(e) => {
                                    if (e.key === 'Enter' && !e.shiftKey) {
                                        e.preventDefault();
                                        handleSuggestStream(e);
                                    }
                                }}
                            />
                            <button
                                type="submit"
                                className="pl-4 pr-2 border-l border-[#D9D9D9] bg-transparent"
                                disabled={isLoading}
                            >
                                {isLoading ? (
                                    <svg
                                        width="14"
                                        height="14"
                                        viewBox="0 0 24 14"
                                        xmlns="http://www.w3.org/2000/svg"
                                    >
                                        <circle cx="4" cy="12" r="3">
                                            <animate
                                                id="spinner_qFRN"
                                                begin="0;spinner_OcgL.end+0.25s"
                                                attributeName="cy"
                                                calcMode="spline"
                                                dur="0.6s"
                                                values="12;6;12"
                                                keySplines=".33,.66,.66,1;.33,0,.66,.33"
                                            />
                                        </circle>
                                        <circle cx="12" cy="12" r="3">
                                            <animate
                                                begin="spinner_qFRN.begin+0.1s"
                                                attributeName="cy"
                                                calcMode="spline"
                                                dur="0.6s"
                                                values="12;6;12"
                                                keySplines=".33,.66,.66,1;.33,0,.66,.33"
                                            />
                                        </circle>
                                        <circle cx="20" cy="12" r="3">
                                            <animate
                                                id="spinner_OcgL"
                                                begin="spinner_qFRN.begin+0.2s"
                                                attributeName="cy"
                                                calcMode="spline"
                                                dur="0.6s"
                                                values="12;6;12"
                                                keySplines=".33,.66,.66,1;.33,0,.66,.33"
                                            />
                                        </circle>
                                    </svg>
                                ) : (
                                    'Go'
                                )}
                            </button>
                        </form>
                    </div>

                    {errorMsg && (
                        <div className="mt-2 text-red-500">
                            <strong>Error:</strong> {errorMsg}
                        </div>
                    )}

                    {hasAnyDomains && (
                        <div className="pt-3 space-y-4">
                            {freeDomains.length > 0 && (
                                <details open>
                                    <summary className="cursor-pointer text-sm font-semibold mb-2 ml-2">
                                        Available Domains ({freeDomains.length})
                                    </summary>
                                    <ul className="mt-2 space-y-2">
                                        {freeDomains.map(renderDomainRow)}
                                    </ul>
                                </details>
                            )}

                            {registeredDomains.length > 0 && (
                                <details>
                                    <summary className="cursor-pointer text-sm font-semibold mb-2 ml-2">
                                        Registered Domains (
                                        {registeredDomains.length})
                                    </summary>
                                    <ul className="mt-2 space-y-2">
                                        {registeredDomains.map(renderDomainRow)}
                                    </ul>
                                </details>
                            )}

                            {unknownDomains.length > 0 && (
                                <details>
                                    <summary className="cursor-pointer text-sm font-semibold mb-2 ml-2">
                                        Other ({unknownDomains.length})
                                    </summary>
                                    <ul className="mt-2 space-y-2">
                                        {unknownDomains.map(renderDomainRow)}
                                    </ul>
                                </details>
                            )}
                        </div>
                    )}
                </div>
            </div>

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
                        bringing your business, app, or project to the web.{' '}
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
                        <ul className="mt-2 space-y-2">
                            {exampleDomains.map(renderDomainRow)}
                        </ul>
                    </details>

                    <details>
                        <summary className="cursor-pointer text-sm font-semibold mb-2 ml-2">
                            Registered Domains (
                            {exampleRegisteredDomains.length})
                        </summary>
                        <ul className="mt-2 space-y-2">
                            {exampleRegisteredDomains.map(renderDomainRow)}
                        </ul>
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
                        Describe what you're creating
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
        </main>
    );
}

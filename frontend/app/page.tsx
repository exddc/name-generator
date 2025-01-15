'use client';

import React, { useState } from 'react';
import { motion } from 'motion/react';
import { Button } from '@/components/ui/button';
import { Textarea } from '@/components/ui/textarea';
import { FlipWords } from '@/components/ui/flip-words';
import Typewriter from '@/components/fancy/typewriter';
import { FaqSection } from '@/components/ui/faq';

interface DomainData {
    domain: string;
    status: string;
}

export default function Home() {
    const [userInput, setUserInput] = useState('');
    const [domains, setDomains] = useState<DomainData[]>([]);
    const [errorMsg, setErrorMsg] = useState<string | null>(null);
    const [isLoading, setIsLoading] = useState(false);
    const [textAreaRows, setTextAreaRows] = useState(1);

    const flipwords = ['app', 'service', 'company', 'idea', 'project'];
    const exampleDomains = [
        {
            domain: 'woodcraftstudio.io',
            status: 'free',
        },
        {
            domain: 'bauhausmuenchen.com',
            status: 'free',
        },
        {
            domain: 'privateview.app',
            status: 'free',
        },
        {
            domain: 'beansofsatisfaction.com',
            status: 'free',
        },
        {
            domain: 'dailycup.io',
            status: 'free',
        },
    ];
    const exampleRegisteredDomains = [
        {
            domain: 'woodworks.de',
            status: 'registered',
        },
        {
            domain: 'munichfurniture.com',
            status: 'registered',
        },
        {
            domain: 'baumhaus.eu',
            status: 'registered',
        },
        {
            domain: 'dailycup.com',
            status: 'registered',
        },
    ];

    const faqQuestions = [
        {
            question: 'What is a domain?',
            answer: 'A domain is the web address you enter in your browser to access a specific website. It replaces the numeric IP addresses that computers use to communicate with each other, making it much easier for people to remember and find websites online.',
        },
        {
            question: 'How do I create a good domain?',
            answer: 'Coming up with a good domain name can be challenging, but it`s worth the time. The name should reflect your brand, be memorable, and avoid confusing elements like hyphens and numbers. Think about whether you need a traditional extension like .com or if a regional or newer extension (like .ca or .xyz) might work better. You can also experiment with free brainstorming or slogan generator tools to spark ideas, then consider registering multiple extensions of the same name to protect your brand in the future.',
        },
        {
            question: 'What is important for a domain name?',
            answer: 'Start by thinking about where your business primarily operates and whether a local extension like .ca or .uk would make sense. Research which extensions your competitors use and look for ways to stand out in your market. If you plan to expand internationally, you may want to secure the .com version as well. It`s also smart to see if matching social media handles are available so your brand name is consistent everywhere.',
        },
        {
            question: 'How do I know if a domain is available?',
            answer: 'Every suggested domain gets checked for availability in real-time. If a domain is already registered, you`ll see that information in the results. If it`s available, you can register it through a domain registrar or website-building platform to secure it for your use.',
        },
        {
            question: 'How do I see if a domain is good?',
            answer: 'A good domain name is usually short, memorable, and easy to spell. Avoid adding numbers or special characters that might cause confusion or typos. Ideally, it matches the brand or business you`re creating and gives people an immediate sense of what they can expect from your site.',
        },
        {
            question: 'Can I change my domain name later?',
            answer: 'Yes, you can register a new domain whenever you like, but keep in mind that changing your primary domain can affect brand recognition, search engine rankings, and user familiarity. It`s usually a good idea to pick a name you`ll want to keep long-term so you don`t confuse your audience or have to rebuild your online presence.',
        },
        {
            question: 'Where do I register a domain name?',
            answer: 'You can register domains through dedicated registrars like GoDaddy or Namecheap, or through website-building platforms like Squarespace or Wix that offer domain registration as part of their service. During registration, you`ll provide contact information and pay an annual fee, which you`ll need to renew to keep ownership of your chosen name.',
        },
        {
            question: 'How important is the domain extension?',
            answer: 'Domain extensions like .com, .org, or country-specific options can influence how your website is perceived. A .com address often signals a global presence, while regional extensions can help you emphasize a local or specialized focus. The key is choosing an extension that aligns with your target audience and long-term goals.',
        },
    ];

    const handleSuggestStream = (e: React.FormEvent) => {
        e.preventDefault();
        setIsLoading(true);
        setDomains([]);
        setErrorMsg(null);

        const url = `http://0.0.0.0:8000/v1/suggest_stream?query=${encodeURIComponent(
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

        evtSource.addEventListener('error', (e: any) => {
            console.error('SSE error event:', e.data);
            setErrorMsg(e.data ?? 'Unknown error occurred.');
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
                                ? 'bg-green-300 border-green-800'
                                : item.status === 'registered'
                                ? 'bg-red-300 border-red-800'
                                : 'bg-yellow-200 border-yellow-800') +
                            ' text-black font-semibold text-xs border px-2 flex items-center h-fit rounded-xl'
                        }
                    >
                        {item.status === 'free'
                            ? 'Available'
                            : item.status === 'registered'
                            ? 'Registered'
                            : 'Unknown'}
                    </p>
                    {/* <button
                        className="pl-4 pr-2 border-l border-[#D9D9D9] bg-white"
                        disabled={isLoading}
                    >
                        Generate similar
                    </button> */}
                </div>
            </li>
        );
    }

    return (
        <main className="flex flex-col items-center justify-center pt-40">
            <div
                className={
                    'transition-all duration-1000 flex' +
                    (hasAnyDomains
                        ? ' h-[350px] blur-[180px]'
                        : ' h-[150px] blur-[120px]')
                }
            >
                <div className="animate-[spin_5s_linear_infinite] bg-[conic-gradient(from_90deg_at_50%_50%,#F76363_0%,#3D65F5_100%)] w-[300px] h-full"></div>
                <div className="animate-[spin_10s_linear_infinite] bg-[conic-gradient(from_90deg_at_50%_50%,#C11A1A_0%,#002AC4_100%)] w-[300px] h-full"></div>
            </div>
            <div
                className={
                    'w-full max-w-xl space-y-4 transition-all duration-1000' +
                    (hasAnyDomains ? ' -mt-[450px]' : ' -mt-[200px]')
                }
            >
                <h1 className="text-4xl font-semibold text-center tracking-tight flex flex-col">
                    <span>Generate domain names</span>
                    <span>that are guaranteed available</span>
                </h1>
                <p className="text-center font-light tracking-tight">
                    Get domain options based on your idea that are available to
                    register
                </p>
            </div>

            <div className="w-full max-w-xl space-y-4 mt-6 bg-white p-3 rounded-xl backdrop-blur-md bg-opacity-70 border border-neutral-300">
                <div className="relative overflow-hidden p-[1px] rounded-xl group">
                    <form
                        onSubmit={handleSuggestStream}
                        className="flex border border-[#D9D9D9] px-4 py-2 text-sm justify-between rounded-xl bg-white"
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
                    <span className="absolute inset-[-1000%] animate-[spin_5s_linear_infinite] bg-[conic-gradient(from_90deg_at_50%_50%,#FFB9B9_0%,#E3CBE9_50%,#9FB3FF_100%)] -z-10 opacity-0 group-focus-within:opacity-100" />
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
            <div className="w-full flex mt-48 align-middle justify-center transition-all duration-300 gap-6 px-6 2xl:px-0">
                <div className="w-full max-w-2xl space-y-4 text-left mt-20">
                    <h2 className="text-2xl font-semibold tracking-tight flex flex-col">
                        <span>Get many suggestions</span>
                        <span>
                            and iterations for your
                            <FlipWords words={flipwords} />
                        </span>
                    </h2>
                    <p className="font-light tracking-tight text-balance">
                        Choosing a great domain name is often the first step in
                        bringing your business, app, or project to life. Our AI
                        takes your input and quickly provides available domain
                        names. This means you can skip the guesswork and go
                        straight to securing a name that fits your brand and
                        vision.
                    </p>
                </div>
                <div className="w-full max-w-xl space-y-4 bg-white p-3 rounded-xl backdrop-blur-md bg-opacity-70 border border-neutral-300">
                    <div className="pt-3 space-y-4">
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
            </div>
            <div className="w-full flex mt-48 align-middle justify-center transition-all duration-300 gap-6 px-6 2xl:px-0">
                <div className="relative overflow-hidden p-[1px] rounded-xl group mt-12 w-full max-w-xl">
                    <div className="flex border border-[#D9D9D9] px-4 py-2 text-sm justify-between rounded-xl bg-white">
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
                    <span className="absolute inset-[-1000%] animate-[spin_5s_linear_infinite] bg-[conic-gradient(from_90deg_at_50%_50%,#FFB9B9_0%,#E3CBE9_50%,#9FB3FF_100%)] -z-10 opacity-0 group-focus-within:opacity-100" />
                </div>
                <div className="w-full max-w-xl space-y-4 text-right">
                    <h2 className="text-2xl font-semibold tracking-tight flex flex-col">
                        Explain what your creating
                    </h2>
                    <p className="font-light tracking-tight text-balance">
                        Describe your app, service, or company idea in the
                        search bar. Click "Go" and our AI will generate
                        available domain names based on your input. You get 5
                        available domain names and more that are registered for
                        inspiration or to help you find similar names.
                    </p>
                </div>
            </div>
            <div className="w-full flex mt-48 align-middle justify-center px-6 2xl:px-0">
                <FaqSection
                    title="Frequently Asked Questions"
                    description="Everything you need to know about domains"
                    items={faqQuestions}
                    className="w-full"
                />
            </div>
        </main>
    );
}

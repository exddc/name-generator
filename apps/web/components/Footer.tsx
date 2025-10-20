// Components
import Link from 'next/link';

export default function Footer() {
    return (
        <footer className="px-6 py-12 w-full mt-64 z-10 max-w-7xl mx-auto flex flex-col">
            <div className="flex flex-row justify-between">
                <div className="flex flex-col font-normal text-sm gap-2">
                    <Link href="/" className="font-semibold text-base">
                        Domain Generator
                    </Link>
                    <Link href="/login" className="">
                        Login
                    </Link>
                    <Link href="/top-domains" className="">
                        Top Rated Domains
                    </Link>
                </div>
                <div className="flex flex-col font-normal text-sm text-right gap-2">
                    <span className="font-semibold text-base">
                        Other Projects
                    </span>
                    <Link
                        href="https://gotdoneapp.com"
                        target="_blank"
                        className=""
                    >
                        Got Done App
                    </Link>
                    <Link
                        href="https://svelte-keyboard.timoweiss.me/"
                        target="_blank"
                        className=""
                    >
                        Svelte Mac Keyboard
                    </Link>
                    <Link
                        href="https://box-grid.timoweiss.me/"
                        target="_blank"
                        className=""
                    >
                        Box Grid Generator
                    </Link>
                    <Link
                        href="https://blurry-blob-background.timoweiss.me/"
                        target="_blank"
                        className=""
                    >
                        Animated Blurry Blob Background
                    </Link>
                </div>
            </div>
            <span className="text-sm text-center mt-12">
                <Link href="https://x.com/timooweiss" target="_blank">
                    Built by Timo Weiss
                </Link>
            </span>
            <span className="text-xs text-center flex items-center gap-2 mx-auto mt-2">
                Made in Germany{' '}
                <img src="/germany.svg" alt="Germany" className="size-4" />
            </span>
        </footer>
    );
}

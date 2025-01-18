import CenterUnderline from './ui/Fancy-Underline-Center';
import Link from 'next/link';

export default function Footer() {
    return (
        <footer className="px-6 py-12 w-full border-t border-neutral-200 mt-24">
            <div className="flex flex-row justify-between">
                <div className="flex flex-col font-normal text-sm">
                    <Link href="/" className="font-semibold">
                        Domain Generator
                    </Link>
                    <span>
                        Built by{' '}
                        <Link
                            href="https://x.com/timooweiss"
                            target="_blank"
                            className="font-serif italic"
                        >
                            <CenterUnderline label="@Timo Weiss" />
                        </Link>
                    </span>
                    <span>© Don&apos;t copy my stuff</span>
                </div>
                <div className="flex flex-col font-normal text-sm text-right">
                    <span className="font-semibold">Links</span>
                    <Link
                        href="https://gotdoneapp.com"
                        target="_blank"
                        className=""
                    >
                        <CenterUnderline label="Got Done App" />
                    </Link>
                    <Link
                        href="https://timoweiss.me"
                        target="_blank"
                        className=""
                    >
                        <CenterUnderline label="timoweiss.me" />
                    </Link>
                </div>
            </div>
        </footer>
    );
}

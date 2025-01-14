import CenterUnderline from './ui/Fancy-Underline-Center';

export default function Footer() {
    return (
        <footer className="px-6 py-12 w-full border-t border-neutral-200 mt-24">
            <div className="flex flex-row justify-between">
                <div className="flex flex-col font-normal text-sm">
                    <a href="/" className="font-semibold">
                        Domain Generator
                    </a>
                    <span>
                        Built by{' '}
                        <a
                            href="https://x.com/timooweiss"
                            target="_blank"
                            className="font-serif italic"
                        >
                            <CenterUnderline label="@Timo Weiss" />
                        </a>
                    </span>
                    <span>© Don't copy my stuff</span>
                </div>
                <div className="flex flex-col font-normal text-sm text-right">
                    <span className="font-semibold">Links</span>
                    <a
                        href="https://gotdoneapp.com"
                        target="_blank"
                        className=""
                    >
                        <CenterUnderline label="Got Done App" />
                    </a>
                    <a href="https://timoweiss.me" target="_blank" className="">
                        <CenterUnderline label="timoweiss.me" />
                    </a>
                </div>
            </div>
        </footer>
    );
}

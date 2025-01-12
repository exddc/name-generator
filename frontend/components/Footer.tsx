export default function Footer() {
    return (
        <footer className="px-6 py-3 mt-48">
            <div className="flex flex-row justify-between">
                <a
                    href="/"
                    className="font-normal text-sm justify-center items-center flex"
                >
                    Domain Generator
                </a>
                <a
                    href="https://timoweiss.me"
                    target="_blank"
                    className="font-normal text-sm justify-center items-center flex"
                >
                    Built by Timo Weiss
                </a>
            </div>
        </footer>
    );
}

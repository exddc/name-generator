export default function Header() {
    return (
        <header className="px-6 py-3 sticky top-0 backdrop-blur-sm">
            <div className="flex flex-row justify-between">
                <a
                    href="/"
                    className="font-normal text-sm justify-center items-center flex"
                >
                    Domain Generator
                </a>
                <div className="flex flex-row font-normal text-sm gap-2 tracking-tight">
                    <a
                        href="/"
                        className="bg-black text-white px-3 py-[2px] rounded-[5px] border border-black flex items-center"
                    >
                        Login
                    </a>
                    <a
                        href="/"
                        className="bg-white text-black px-3 py-[2px] rounded-[5px] border border-black flex items-center"
                    >
                        Signup
                    </a>
                </div>
            </div>
        </header>
    );
}

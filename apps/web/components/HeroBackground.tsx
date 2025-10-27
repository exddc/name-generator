export default function HeroBackground() {
    return (
        <div className="flex blur-[130px] z-0 top-0 left-[50%] bg-green-50 w-full justify-center items-center h-screen sticky -mt-[90vh]">
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
    );
}

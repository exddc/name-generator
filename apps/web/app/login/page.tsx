'use client';
export default function Login() {
    return (
        <div className="flex flex-col items-center justify-center my-96">
            <p>User Accounts are coming soon</p>
            <button
                onClick={() => {
                    window.location.href = '/';
                }}
                className="bg-black text-white px-3 py-[2px] rounded-[5px] border border-black flex items-center text-sm mt-4"
            >
                Go back
            </button>
        </div>
    );
}

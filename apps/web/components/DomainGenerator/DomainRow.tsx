// Libraries
import { DomainData } from '@/lib/types';

// Components
import Link from 'next/link';

export default function DomainRow({ domain }: { domain: DomainData }) {
    return (
        <div className="flex border border-gray-50 px-4 py-3 rounded-xl text-sm justify-between bg-white bg-opacity-40 backdrop-blur-lg hover:bg-opacity-60">
            <Link
                href={'https://' + domain.domain}
                target="_blank"
                rel="noreferrer"
                className="font-semibold"
            >
                {domain.domain}
            </Link>
            <div className="flex gap-4 items-center">
                <span className="text-xs hover:cursor-pointer">
                    Suggest similar
                </span>
                <span
                    className={
                        (domain.status === 'free'
                            ? 'bg-green-500/30 border-green-700'
                            : domain.status === 'registered'
                            ? 'bg-red-500/30 border-red-700'
                            : 'bg-yellow-500/30 border-yellow-700') +
                        ' text-black font-semibold text-[0.65rem] border px-2 flex items-center h-[18px] rounded-xl'
                    }
                >
                    {domain.status === 'free'
                        ? 'Available'
                        : domain.status === 'registered'
                        ? 'Registered'
                        : 'Unknown'}
                </span>
            </div>
        </div>
    );
}

// Libraries
import { Domain, DomainStatusColor } from '@/lib/types';
import { cn } from '@/lib/utils';

// Components
import Link from 'next/link';

export default function DomainRow({ domain }: { domain: Domain }) {
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
                    className={cn(
                        DomainStatusColor[domain.status],
                        'text-neutral-800 font-semibold text-[0.6rem] border px-1.5 flex items-center h-[20px] rounded-xl'
                    )}
                >
                    {domain.status}
                </span>
            </div>
        </div>
    );
}

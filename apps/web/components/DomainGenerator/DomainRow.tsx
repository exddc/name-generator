// Libraries
import { Domain, DomainStatusColor } from '@/lib/types';
import { cn } from '@/lib/utils';

// Components
import Link from 'next/link';
import { ChevronDown, Heart, ShoppingCart } from 'lucide-react';

export default function DomainRow({ domain }: { domain: Domain }) {
    return (
        <div className="flex border border-gray-50 px-4 py-3 rounded-xl text-sm justify-between bg-white bg-opacity-40 backdrop-blur-lg hover:bg-opacity-60">
            <div className="flex items-center gap-4">
                <Link
                    href={'https://' + domain.domain}
                    target="_blank"
                    rel="noreferrer"
                    className="font-semibold"
                >
                    {domain.domain}
                </Link>
                <span
                    className={cn(
                        DomainStatusColor[domain.status],
                        'text-neutral-800 font-semibold text-[0.4rem] border px-1 flex items-center h-[14px] rounded-xl'
                    )}
                >
                    {domain.status}
                </span>
            </div>
            <div className="flex gap-4 items-center justify-end">
                <button className="hover:cursor-pointer hover:scale-110 transition-all duration-300">
                    <Heart className="size-4" strokeWidth={1.75} />
                </button>
                <button className="hover:cursor-pointer hover:scale-110 transition-all duration-300">
                    <ShoppingCart className="size-4" strokeWidth={1.75} />
                </button>
                <button className="hover:cursor-pointer hover:scale-110 transition-all duration-300">
                    <ChevronDown className="size-4" strokeWidth={1.75} />
                </button>
            </div>
        </div>
    );
}

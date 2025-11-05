'use client';

// Libraries
import React, { useEffect, useState, useMemo } from 'react';
import { useRouter, useSearchParams } from 'next/navigation';
import {
    useReactTable,
    getCoreRowModel,
    getSortedRowModel,
    flexRender,
    type ColumnDef,
    type SortingState,
} from '@tanstack/react-table';
import {
    Domain,
    DomainStatus,
    DomainStatusColor,
    RatingRequestBody,
} from '@/lib/types';
import { cn, getAnonRandomId } from '@/lib/utils';
import {
    ArrowUpDown,
    ArrowUp,
    ArrowDown,
    ShoppingCart,
    ThumbsUp,
    ThumbsDown,
} from 'lucide-react';
import { useSession } from '@/lib/auth-client';

// Components
import { Card } from '@/components/ui/card';
import HeroBackground from '@/components/HeroBackground';
import { Input } from '@/components/ui/input';
import { Button } from '@/components/ui/button';
import {
    Table,
    TableBody,
    TableCell,
    TableHead,
    TableHeader,
    TableRow,
} from '@/components/ui/table';
import { DomainRow } from '@/components/DomainGenerator';

const TOP_DOMAINS_API_URL = `${process.env.NEXT_PUBLIC_API_URL}/v1/domain/top`;
const RATING_API_URL = `${process.env.NEXT_PUBLIC_API_URL}/v1/domain/rating`;
const RATINGS_GET_URL = `${process.env.NEXT_PUBLIC_API_URL}/v1/domain/rating`;

type SortBy =
    | 'rating'
    | 'domain'
    | 'tld'
    | 'status'
    | 'last_checked'
    | 'created_at';
type SortOrder = 'asc' | 'desc';

export default function TopDomains() {
    const router = useRouter();
    const searchParams = useSearchParams();
    const { data: session } = useSession();
    const [domains, setDomains] = useState<Domain[]>([]);
    const [isLoading, setIsLoading] = useState(true);
    const [showLoadingIndicator, setShowLoadingIndicator] = useState(false);
    const [searchQuery, setSearchQuery] = useState('');
    const [debouncedSearchQuery, setDebouncedSearchQuery] = useState('');
    const [page, setPage] = useState(1);
    const [total, setTotal] = useState(0);
    const [sortBy, setSortBy] = useState<SortBy>('rating');
    const [sortOrder, setSortOrder] = useState<SortOrder>('desc');
    const [votingDomain, setVotingDomain] = useState<string | null>(null);
    const [domainVotes, setDomainVotes] = useState<Map<string, 1 | -1>>(
        new Map()
    );
    const pageSize = 20;

    const [sorting, setSorting] = useState<SortingState>([
        { id: 'rating', desc: true },
    ]);

    // Helper function to cycle through sort states: none → asc → desc → none
    const handleSortToggle = (columnId: string) => {
        const isCurrentlySorted = sortBy === columnId;

        let newSortBy: SortBy = 'rating';
        let newSortOrder: SortOrder = 'desc';
        let newSorting: SortingState = [];

        if (!isCurrentlySorted) {
            // No sort or different column sorted → Ascending
            newSortBy = columnId as SortBy;
            newSortOrder = 'asc';
            newSorting = [{ id: columnId, desc: false }];
        } else if (sortOrder === 'asc') {
            // Ascending → Descending
            newSortBy = columnId as SortBy;
            newSortOrder = 'desc';
            newSorting = [{ id: columnId, desc: true }];
        } else {
            // Descending → No sort (reset to default: rating desc)
            newSortBy = 'rating';
            newSortOrder = 'desc';
            newSorting = [{ id: 'rating', desc: true }];
        }

        setSortBy(newSortBy);
        setSortOrder(newSortOrder);
        setSorting(newSorting);
    };

    useEffect(() => {
        const timer = setTimeout(() => {
            setDebouncedSearchQuery(searchQuery);
            setPage(1);
        }, 500);

        return () => clearTimeout(timer);
    }, [searchQuery]);

    useEffect(() => {
        let loadingTimer: NodeJS.Timeout | null = null;

        if (isLoading) {
            loadingTimer = setTimeout(() => {
                setShowLoadingIndicator(true);
            }, 1000);
        } else {
            setShowLoadingIndicator(false);
        }

        return () => {
            if (loadingTimer) {
                clearTimeout(loadingTimer);
            }
        };
    }, [isLoading]);

    // Fetch existing ratings
    useEffect(() => {
        const fetchRatings = async () => {
            try {
                const params = new URLSearchParams();
                if (session?.user?.id) {
                    params.append('user_id', session.user.id);
                } else {
                    params.append('anon_random_id', getAnonRandomId());
                }
                params.append('page_size', '100');

                const response = await fetch(
                    `${RATINGS_GET_URL}?${params.toString()}`
                );

                if (response.ok) {
                    const data = await response.json();
                    const votesMap = new Map<string, 1 | -1>();
                    data.ratings?.forEach(
                        (rating: { domain: string; vote: number }) => {
                            votesMap.set(rating.domain, rating.vote as 1 | -1);
                        }
                    );
                    setDomainVotes(votesMap);
                }
            } catch (error) {
                console.error('Failed to fetch ratings:', error);
            }
        };

        fetchRatings();
    }, [session?.user?.id]);

    const handleVote = async (domain: string, vote: number) => {
        if (votingDomain === domain) {
            return;
        }

        setVotingDomain(domain);

        try {
            let requestBody: RatingRequestBody = {
                domain,
                vote: vote as 1 | -1,
            };

            if (session?.user?.id) {
                requestBody.user_id = session.user.id;
            } else {
                requestBody.anon_random_id = getAnonRandomId();
            }

            const response = await fetch(RATING_API_URL, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify(requestBody),
            });

            if (!response.ok) {
                const errorData = await response.json().catch(() => ({}));
                throw new Error(
                    errorData.detail ||
                        `Failed to submit vote: ${response.statusText}`
                );
            }

            const result = await response.json();

            setDomainVotes((prev) => {
                const next = new Map(prev);
                next.set(domain, vote as 1 | -1);
                return next;
            });
        } catch (error) {
            console.error('Failed to submit vote:', error);
        } finally {
            setVotingDomain(null);
        }
    };

    const getVoteForDomain = (domainName: string): 1 | -1 | undefined => {
        return domainVotes.get(domainName);
    };

    const getSortIndicator = (columnId: string) => {
        if (sortBy !== columnId) {
            return <ArrowUpDown className="h-4 w-4 opacity-50" />;
        }
        return sortOrder === 'desc' ? (
            <ArrowDown className="h-4 w-4" />
        ) : (
            <ArrowUp className="h-4 w-4" />
        );
    };

    const columns = useMemo<ColumnDef<Domain>[]>(
        () => [
            {
                accessorKey: 'domain',
                header: () => (
                    <button
                        className="flex items-center gap-2 hover:text-gray-900"
                        onClick={() => handleSortToggle('domain')}
                    >
                        Domain
                        {getSortIndicator('domain')}
                    </button>
                ),
                cell: ({ row }) => (
                    <a
                        href={`https://${row.original.domain}`}
                        target="_blank"
                        rel="noreferrer"
                        className="font-semibold hover:underline"
                    >
                        {row.original.domain}
                    </a>
                ),
            },
            {
                id: 'rating_actions',
                header: () => <div></div>,
                cell: ({ row }) => {
                    const domainName = row.original.domain;
                    const currentVote = getVoteForDomain(domainName);
                    return (
                        <div className="flex items-center justify-center gap-1">
                            <button
                                className={cn(
                                    'hover:cursor-pointer hover:scale-110 transition-all duration-300',
                                    currentVote === 1 && 'text-green-600'
                                )}
                                onClick={() => handleVote(domainName, 1)}
                                disabled={votingDomain === domainName}
                            >
                                <ThumbsUp
                                    className={cn(
                                        'size-3',
                                        currentVote === 1 && 'text-green-600'
                                    )}
                                    strokeWidth={1.75}
                                />
                            </button>
                            <button
                                className={cn(
                                    'hover:cursor-pointer hover:scale-110 transition-all duration-300',
                                    currentVote === -1 && 'text-red-600'
                                )}
                                onClick={() => handleVote(domainName, -1)}
                                disabled={votingDomain === domainName}
                            >
                                <ThumbsDown
                                    className={cn(
                                        'size-3',
                                        currentVote === -1 && 'text-red-600'
                                    )}
                                    strokeWidth={1.75}
                                />
                            </button>
                        </div>
                    );
                },
            },
            {
                accessorKey: 'status',
                header: () => (
                    <button
                        className="flex items-center justify-center gap-2 hover:text-gray-900 w-full"
                        onClick={() => handleSortToggle('status')}
                    >
                        Status
                        {getSortIndicator('status')}
                    </button>
                ),
                cell: ({ row }) => (
                    <div className="flex justify-center">
                        <span
                            className={cn(
                                DomainStatusColor[row.original.status],
                                'text-neutral-800 font-semibold text-xs border px-2 py-1 rounded'
                            )}
                        >
                            {row.original.status}
                        </span>
                    </div>
                ),
            },
            {
                accessorKey: 'updated_at',
                id: 'last_checked',
                header: () => (
                    <button
                        className="flex items-center justify-center gap-2 hover:text-gray-900 w-full"
                        onClick={() => handleSortToggle('last_checked')}
                    >
                        Last Checked
                        {getSortIndicator('last_checked')}
                    </button>
                ),
                cell: ({ row }) => {
                    const date = row.original.updated_at
                        ? new Date(row.original.updated_at)
                        : null;
                    return (
                        <div className="text-center">
                            <span className="text-sm text-gray-600">
                                {date
                                    ? date.toLocaleDateString('en-US', {
                                          year: 'numeric',
                                          month: 'short',
                                          day: 'numeric',
                                      })
                                    : 'N/A'}
                            </span>
                        </div>
                    );
                },
            },
            {
                accessorKey: 'rating',
                header: () => (
                    <button
                        className="flex items-center justify-center gap-2 hover:text-gray-900 w-full"
                        onClick={() => handleSortToggle('rating')}
                    >
                        Rating
                        {getSortIndicator('rating')}
                    </button>
                ),
                cell: ({ row }) => (
                    <div className="text-center">
                        <span className="font-medium">
                            {row.original.rating ?? 0}
                        </span>
                    </div>
                ),
            },

            {
                accessorKey: 'total_ratings',
                header: () => <div className="text-center">Total Ratings</div>,
                cell: ({ row }) => (
                    <div className="text-center">
                        <span className="font-medium">
                            {row.original.total_ratings ?? 0}
                        </span>
                    </div>
                ),
            },
            {
                accessorKey: 'model',
                header: () => <div className="text-center">Model</div>,
                cell: ({ row }) => {
                    const model = row.original.model || '';
                    const displayModel =
                        model === 'variants-check' || model === 'variants'
                            ? 'TLD Variation'
                            : model || 'N/A';
                    return (
                        <div className="text-center">
                            <span className="text-sm text-gray-600">
                                {displayModel}
                            </span>
                        </div>
                    );
                },
            },
            {
                id: 'actions',
                header: () => <div></div>,
                cell: ({ row }) => (
                    <div className="flex justify-center">
                        <button className="hover:cursor-pointer hover:scale-110 transition-all duration-300">
                            <ShoppingCart
                                className="size-4"
                                strokeWidth={1.75}
                            />
                        </button>
                    </div>
                ),
            },
        ],
        [sortBy, sortOrder, domainVotes, votingDomain]
    );

    const table = useReactTable({
        data: domains,
        columns,
        getCoreRowModel: getCoreRowModel(),
        getSortedRowModel: getSortedRowModel(),
        onSortingChange: setSorting,
        state: {
            sorting,
        },
        manualSorting: true,
    });

    useEffect(() => {
        const fetchDomains = async () => {
            setIsLoading(true);
            try {
                const params = new URLSearchParams();
                params.append('page', page.toString());
                params.append('page_size', pageSize.toString());
                params.append('sort_by', sortBy);
                params.append('order', sortOrder);

                if (debouncedSearchQuery.trim()) {
                    params.append('search', debouncedSearchQuery.trim());
                }

                const response = await fetch(
                    `${TOP_DOMAINS_API_URL}?${params.toString()}`
                );

                if (response.ok) {
                    const data = await response.json();
                    const domainObjects: Domain[] =
                        data.suggestions?.map(
                            (suggestion: {
                                domain: string;
                                tld: string;
                                status: DomainStatus;
                                rating?: number;
                                created_at: string;
                                updated_at: string;
                                total_ratings?: number;
                                model?: string;
                                prompt?: string;
                            }) => {
                                return {
                                    domain: suggestion.domain,
                                    tld: suggestion.tld,
                                    status: suggestion.status,
                                    rating: suggestion.rating,
                                    created_at: suggestion.created_at,
                                    updated_at: suggestion.updated_at,
                                    total_ratings: suggestion.total_ratings,
                                    model: suggestion.model,
                                    prompt: suggestion.prompt,
                                };
                            }
                        ) || [];
                    setDomains(domainObjects);
                    setTotal(data.total || 0);
                }
            } catch (error) {
                console.error('Failed to fetch top domains:', error);
            } finally {
                setIsLoading(false);
            }
        };

        fetchDomains();
    }, [page, sortBy, sortOrder, debouncedSearchQuery]);

    const handleSearch = (e: React.FormEvent) => {
        e.preventDefault();
        setPage(1);
    };

    const totalPages = Math.ceil(total / pageSize);

    return (
        <main className="flex flex-col items-center justify-center max-w-6xl gap-8 mx-auto px-6 xl:px-0">
            <HeroBackground />
            <div className="flex flex-col gap-8 w-full items-center justify-center">
                <Card className="w-full flex flex-col gap-4">
                    <div className="mb-6">
                        <h1 className="text-3xl font-semibold tracking-tight mb-2">
                            Top Rated Domains
                        </h1>
                        <p className="text-gray-600">
                            Explore and get inspired by the top rated domains
                            that are still available
                        </p>
                    </div>

                    <div className="flex gap-2">
                        <Input
                            type="text"
                            placeholder="Search for a domain or idea..."
                            value={searchQuery}
                            onChange={(e) => setSearchQuery(e.target.value)}
                            className="flex-1"
                        />
                    </div>

                    {showLoadingIndicator ? (
                        <div className="text-center py-8">
                            <p className="text-gray-600">Loading domains...</p>
                        </div>
                    ) : domains.length === 0 ? (
                        <div className="text-center py-8">
                            <p className="text-gray-600 mb-4">
                                {debouncedSearchQuery.trim()
                                    ? `No domains found. You can generate domains for this search.`
                                    : 'No domains found.'}
                            </p>
                            <Button
                                onClick={() =>
                                    router.push(
                                        debouncedSearchQuery.trim()
                                            ? `/?search=${encodeURIComponent(
                                                  debouncedSearchQuery.trim()
                                              )}`
                                            : '/'
                                    )
                                }
                            >
                                {debouncedSearchQuery.trim()
                                    ? 'Generate Domains'
                                    : 'Go to Main Page'}
                            </Button>
                        </div>
                    ) : (
                        <div className="w-full">
                            <Table>
                                <TableHeader>
                                    {table
                                        .getHeaderGroups()
                                        .map((headerGroup) => (
                                            <TableRow key={headerGroup.id}>
                                                {headerGroup.headers.map(
                                                    (header) => (
                                                        <TableHead
                                                            key={header.id}
                                                        >
                                                            {header.isPlaceholder
                                                                ? null
                                                                : flexRender(
                                                                      header
                                                                          .column
                                                                          .columnDef
                                                                          .header,
                                                                      header.getContext()
                                                                  )}
                                                        </TableHead>
                                                    )
                                                )}
                                            </TableRow>
                                        ))}
                                </TableHeader>
                                <TableBody>
                                    {table.getRowModel().rows?.length ? (
                                        table.getRowModel().rows.map((row) => (
                                            <TableRow
                                                key={row.id}
                                                data-state={
                                                    row.getIsSelected() &&
                                                    'selected'
                                                }
                                            >
                                                {row
                                                    .getVisibleCells()
                                                    .map((cell) => (
                                                        <TableCell
                                                            key={cell.id}
                                                        >
                                                            {flexRender(
                                                                cell.column
                                                                    .columnDef
                                                                    .cell,
                                                                cell.getContext()
                                                            )}
                                                        </TableCell>
                                                    ))}
                                            </TableRow>
                                        ))
                                    ) : (
                                        <TableRow>
                                            <TableCell
                                                colSpan={columns.length}
                                                className="h-24 text-center"
                                            >
                                                No results.
                                            </TableCell>
                                        </TableRow>
                                    )}
                                </TableBody>
                            </Table>

                            {totalPages > 1 && (
                                <div className="flex items-center justify-between w-full">
                                    <Button
                                        variant="outline"
                                        onClick={() =>
                                            setPage((p) => Math.max(1, p - 1))
                                        }
                                        disabled={page === 1}
                                    >
                                        Previous
                                    </Button>
                                    <span className="text-sm text-gray-600">
                                        Page {page} of {totalPages} ({total}{' '}
                                        total)
                                    </span>
                                    <Button
                                        variant="outline"
                                        onClick={() =>
                                            setPage((p) =>
                                                Math.min(totalPages, p + 1)
                                            )
                                        }
                                        disabled={page === totalPages}
                                    >
                                        Next
                                    </Button>
                                </div>
                            )}
                        </div>
                    )}
                </Card>
            </div>
        </main>
    );
}

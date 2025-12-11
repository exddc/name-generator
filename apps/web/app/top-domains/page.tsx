'use client';

// Libraries
import { useEffect, useState, useMemo } from 'react';
import { useRouter } from 'next/navigation';
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
    FavoriteRequestBody,
} from '@/lib/types';
import { cn, getDomainRegistrarUrl } from '@/lib/utils';
import {
    ArrowUpDown,
    ArrowUp,
    ArrowDown,
    ShoppingCart,
    ThumbsUp,
    ThumbsDown,
    Heart,
} from 'lucide-react';
import { useSession } from '@/lib/auth-client';
import { toast } from '@/components/ui/sonner';

// Components
import { Card } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Button } from '@/components/ui/button';
import { Skeleton } from '@/components/ui/skeleton';
import {
    Table,
    TableBody,
    TableCell,
    TableHead,
    TableHeader,
    TableRow,
} from '@/components/ui/table';
import Link from 'next/link';

import { PageShell, PageHeader } from '@/components/page-layout';
import { apiFetch } from '@/lib/api-client';

const TOP_DOMAINS_API_URL = `${process.env.NEXT_PUBLIC_API_URL}/v1/domain/top`;
const RATING_API_URL = `${process.env.NEXT_PUBLIC_API_URL}/v1/domain/rating`;
const RATINGS_GET_URL = `${process.env.NEXT_PUBLIC_API_URL}/v1/domain/rating`;
const FAVORITE_API_URL = `${process.env.NEXT_PUBLIC_API_URL}/v1/user/favorite`;

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
    const { data: session } = useSession();
    const [domains, setDomains] = useState<Domain[]>([]);
    const [isLoading, setIsLoading] = useState(true);
    const [hasError, setHasError] = useState(false);
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
    const [favoritingDomain, setFavoritingDomain] = useState<string | null>(
        null
    );
    const pageSize = 20;

    const [statusFilter, setStatusFilter] = useState<'available' | null>(
        'available'
    );
    const [domainLengthFilter, setDomainLengthFilter] = useState<
        null | '<5' | '<10'
    >(null);
    const [tldFilter, setTldFilter] = useState<Set<string>>(new Set());
    const [allDomains, setAllDomains] = useState<Domain[]>([]);

    const [sorting, setSorting] = useState<SortingState>([
        { id: 'rating', desc: true },
    ]);

    const handleSortToggle = (columnId: string) => {
        const isCurrentlySorted = sortBy === columnId;

        let newSortBy: SortBy = 'rating';
        let newSortOrder: SortOrder = 'desc';
        let newSorting: SortingState = [];

        if (!isCurrentlySorted) {
            newSortBy = columnId as SortBy;
            newSortOrder = 'asc';
            newSorting = [{ id: columnId, desc: false }];
        } else if (sortOrder === 'asc') {
            newSortBy = columnId as SortBy;
            newSortOrder = 'desc';
            newSorting = [{ id: columnId, desc: true }];
        } else {
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

    useEffect(() => {
        const fetchRatings = async () => {
            try {
                const params = new URLSearchParams();
                params.append('page', '1');
                params.append('page_size', '100');

                const response = await apiFetch(
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
                if ((error as Error)?.message !== 'AUTH_REQUIRED') {
                    console.warn('Failed to fetch ratings:', error);
                }
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

            const response = await apiFetch(RATING_API_URL, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify(requestBody),
            });

            if (!response.ok) {
                const errorData = await response.json().catch(() => ({}));
                const errorMessage =
                    errorData.detail?.message ||
                    errorData.detail ||
                    'Failed to submit vote';
                toast.error(errorMessage);
                return;
            }

            setDomainVotes((prev) => {
                const next = new Map(prev);
                next.set(domain, vote as 1 | -1);
                return next;
            });
        } catch (error) {
            if ((error as Error)?.message !== 'AUTH_REQUIRED') {
                console.error('Failed to submit vote:', error);
                toast.error('Failed to submit vote. Please try again.');
            }
        } finally {
            setVotingDomain(null);
        }
    };

    const getVoteForDomain = (domainName: string): 1 | -1 | undefined => {
        return domainVotes.get(domainName);
    };

    const handleFavorite = async (domain: string) => {
        if (!session?.user?.id) {
            toast.info('You need to be logged in to favorite domains', {
                description: 'Sign in to save your favorite domain names.',
            });
            return;
        }

        if (favoritingDomain === domain) {
            return;
        }

        setFavoritingDomain(domain);

        try {
            const domainObj = allDomains.find((d) => d.domain === domain);
            const isFavorited = domainObj?.is_favorite ?? false;
            const action = isFavorited ? 'unfav' : 'fav';

            const requestBody: FavoriteRequestBody = {
                domain,
                user_id: session.user.id,
                action,
            };

            const response = await apiFetch(FAVORITE_API_URL, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify(requestBody),
            });

            if (!response.ok) {
                const errorData = await response.json().catch(() => ({}));
                const errorMessage =
                    errorData.detail?.message ||
                    errorData.detail ||
                    `Failed to ${
                        action === 'fav' ? 'favorite' : 'unfavorite'
                    } domain`;
                toast.error(errorMessage);
                return;
            }

            // Update the domain's is_favorite status
            setAllDomains((prev) =>
                prev.map((d) =>
                    d.domain === domain
                        ? { ...d, is_favorite: !isFavorited }
                        : d
                )
            );

            // Show success toast
            if (action === 'fav') {
                toast.success(`Added ${domain} to favorites`);
            }
        } catch (error) {
            if ((error as Error)?.message === 'AUTH_REQUIRED') {
                toast.info('Sign in to favorite domains', {
                    description: 'Log in to save your favorite domain names.',
                });
            } else {
                console.error('Failed to toggle favorite:', error);
                toast.error('Failed to update favorite. Please try again.');
            }
        } finally {
            setFavoritingDomain(null);
        }
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
            /* {
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
            }, */
            {
                id: 'actions',
                header: () => <div></div>,
                cell: ({ row }) => {
                    const domainName = row.original.domain;
                    const isFavorited = row.original.is_favorite ?? false;
                    return (
                        <div className="flex justify-center items-center gap-2">
                            {session?.user?.id && (
                                <button
                                    className={cn(
                                        'hover:cursor-pointer hover:scale-110 transition-all duration-300',
                                        isFavorited && 'text-red-600'
                                    )}
                                    onClick={() => handleFavorite(domainName)}
                                    disabled={favoritingDomain === domainName}
                                >
                                    <Heart
                                        className={cn(
                                            'size-4',
                                            isFavorited &&
                                                'fill-red-600 text-red-600'
                                        )}
                                        strokeWidth={1.75}
                                    />
                                </button>
                            )}
                            <Link
                                className="hover:cursor-pointer hover:scale-110 transition-all duration-300"
                                href={getDomainRegistrarUrl(domainName)}
                                target="_blank"
                                rel="noreferrer"
                            >
                                <ShoppingCart
                                    className="size-4"
                                    strokeWidth={1.75}
                                />
                            </Link>
                        </div>
                    );
                },
            },
        ],
        [
            sortBy,
            sortOrder,
            domainVotes,
            votingDomain,
            favoritingDomain,
            getVoteForDomain,
            session?.user?.id,
        ]
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

    const fetchDomains = async () => {
        setIsLoading(true);
        setHasError(false);
        try {
            const params = new URLSearchParams();
            params.append('page', page.toString());
            params.append('page_size', pageSize.toString());
            params.append('sort_by', sortBy);
            params.append('order', sortOrder);

            if (statusFilter) {
                params.append('status', statusFilter);
            } else {
                params.append('status', '');
            }

            if (debouncedSearchQuery.trim()) {
                params.append('search', debouncedSearchQuery.trim());
            }

            const response = await apiFetch(
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
                            is_favorite?: boolean | null;
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
                                is_favorite: suggestion.is_favorite,
                            };
                        }
                    ) || [];
                setAllDomains(domainObjects);
                setTotal(data.total || 0);
            } else {
                setHasError(true);
            }
        } catch (error) {
            if ((error as Error)?.message === 'AUTH_REQUIRED') {
                toast.info('Sign in again to refresh top domains.');
            } else {
                console.warn('Failed to fetch top domains:', error);
            }
            setHasError(true);
        } finally {
            setIsLoading(false);
        }
    };

    useEffect(() => {
        fetchDomains();
    }, [
        page,
        sortBy,
        sortOrder,
        debouncedSearchQuery,
        statusFilter,
        session?.user?.id,
    ]);

    useEffect(() => {
        let filtered = [...allDomains];

        if (domainLengthFilter === '<5') {
            filtered = filtered.filter((d) => {
                const domainName = d.domain.split('.')[0];
                return domainName.length < 5;
            });
        } else if (domainLengthFilter === '<10') {
            filtered = filtered.filter((d) => {
                const domainName = d.domain.split('.')[0];
                return domainName.length < 10;
            });
        }

        if (tldFilter.size > 0) {
            filtered = filtered.filter((d) => tldFilter.has(d.tld));
        }

        setDomains(filtered);
    }, [allDomains, domainLengthFilter, tldFilter]);

    const uniqueTlds = useMemo(() => {
        const tlds = new Set<string>();
        allDomains.forEach((d) => tlds.add(d.tld));
        return Array.from(tlds).sort();
    }, [allDomains]);

    const totalPages = Math.ceil(total / pageSize);

    return (
        <PageShell>
            <PageHeader
                title="Top Rated Domains"
                description="Explore and get inspired by the top rated domains that are still available"
            />

            <Card className="w-full max-w-6xl flex flex-col gap-4 min-h-[800px] xl:w-[1152px] border-neutral-200">
                <Input
                    type="text"
                    placeholder="Search for a domain or idea..."
                    value={searchQuery}
                    onChange={(e) => setSearchQuery(e.target.value)}
                    className="w-full"
                />

                {/* Filter Buttons */}
                <div className="flex flex-row gap-4">
                    {/* Status Filter */}
                    <div className="flex flex-wrap items-center gap-2">
                        <span className="text-xs font-medium text-gray-700">
                            Status
                        </span>
                        <Button
                            variant={
                                statusFilter === 'available'
                                    ? 'default'
                                    : 'outline'
                            }
                            size="xs"
                            onClick={() => {
                                setStatusFilter(
                                    statusFilter === 'available'
                                        ? null
                                        : 'available'
                                );
                                setPage(1);
                            }}
                        >
                            Available
                        </Button>
                    </div>

                    {/* Domain Length Filter */}
                    <div className="flex flex-wrap items-center gap-2">
                        <span className="text-xs font-medium text-gray-700">
                            Domain Length
                        </span>
                        <Button
                            variant={
                                domainLengthFilter === '<5'
                                    ? 'default'
                                    : 'outline'
                            }
                            size="xs"
                            onClick={() => {
                                setDomainLengthFilter(
                                    domainLengthFilter === '<5' ? null : '<5'
                                );
                                setPage(1);
                            }}
                        >
                            &lt;5 chars
                        </Button>
                        <Button
                            variant={
                                domainLengthFilter === '<10'
                                    ? 'default'
                                    : 'outline'
                            }
                            size="xs"
                            onClick={() => {
                                setDomainLengthFilter(
                                    domainLengthFilter === '<10' ? null : '<10'
                                );
                                setPage(1);
                            }}
                        >
                            &lt;10 chars
                        </Button>
                    </div>

                    {/* TLD Filter */}
                    {uniqueTlds.length > 0 && (
                        <div className="flex flex-wrap items-center gap-2">
                            <span className="text-xs font-medium text-gray-700">
                                TLD
                            </span>
                            {tldFilter.size > 0 && (
                                <Button
                                    variant="outline"
                                    size="xs"
                                    onClick={() => {
                                        setTldFilter(new Set());
                                        setPage(1);
                                    }}
                                >
                                    Clear ({tldFilter.size})
                                </Button>
                            )}
                            {uniqueTlds.slice(0, 10).map((tld) => (
                                <Button
                                    key={tld}
                                    variant={
                                        tldFilter.has(tld)
                                            ? 'default'
                                            : 'outline'
                                    }
                                    size="xs"
                                    onClick={() => {
                                        setTldFilter((prev) => {
                                            const next = new Set(prev);
                                            if (next.has(tld)) {
                                                next.delete(tld);
                                            } else {
                                                next.add(tld);
                                            }
                                            return next;
                                        });
                                        setPage(1);
                                    }}
                                >
                                    .{tld}
                                </Button>
                            ))}
                            {uniqueTlds.length > 10 && (
                                <span className="text-xs text-gray-500">
                                    +{uniqueTlds.length - 10} more
                                </span>
                            )}
                        </div>
                    )}
                </div>

                {hasError ? (
                    <div className="text-center py-8 flex-1 min-h-[500px] flex flex-col items-center justify-center space-y-4">
                        <div className="space-y-2">
                            <h3 className="text-lg font-semibold text-neutral-700">
                                Failed to load domains
                            </h3>
                            <p className="text-neutral-600 max-w-md mx-auto">
                                We encountered an error while fetching the top
                                domains. Please check your connection and try
                                again.
                            </p>
                        </div>
                    </div>
                ) : showLoadingIndicator ? (
                    <div className="w-full flex-1 min-h-[500px] space-y-4 p-4">
                        {[...Array(10)].map((_, i) => (
                            <div key={i} className="flex gap-4 items-center">
                                <Skeleton className="h-12 w-full" />
                            </div>
                        ))}
                    </div>
                ) : domains.length === 0 ? (
                    <div className="text-center py-8 flex-1 min-h-[500px] flex flex-col items-center justify-center">
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
                                : 'Generate Domains'}
                        </Button>
                    </div>
                ) : (
                    <div className="w-full flex-1 min-h-[500px] flex flex-col">
                        <div className="flex-1 overflow-auto w-full">
                            <Table className="w-full">
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
                        </div>

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
                                    Page {page} of {totalPages} ({total} total)
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

            <div
                id="get-started"
                className="w-full flex align-middle justify-center gap-12 z-10 items-center"
            >
                <div className="w-full flex flex-col gap-4 text-center">
                    <h2 className="text-3xl font-heading font-semibold tracking-tight flex flex-col text-balance">
                        Did not find a good match for you?
                    </h2>
                    <p className="font-light text-balance text-lg">
                        Get at least 5 avaialbe domains specificlly tailored for
                        your idea and vision.
                    </p>
                    <Link
                        href="/"
                        className={cn(
                            'inline-flex items-center justify-center gap-2 whitespace-nowrap rounded-md text-sm font-medium transition-colors focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring disabled:pointer-events-none disabled:opacity-50 [&_svg]:pointer-events-none [&_svg]:size-4 [&_svg]:shrink-0',
                            'bg-primary text-primary-foreground shadow hover:bg-primary/90',
                            'h-9 px-4 py-2',
                            'w-fit mx-auto mt-6'
                        )}
                    >
                        Generate Domains
                    </Link>
                </div>
            </div>
        </PageShell>
    );
}

'use client';

import React, { useEffect, useMemo, useState } from 'react';
import {
    ThumbsUp,
    ThumbsDown,
    ChevronLeft,
    ChevronRight,
    ChevronUp,
    ChevronDown,
} from 'lucide-react';
import Link from 'next/link';
import {
    useReactTable,
    getCoreRowModel,
    getPaginationRowModel,
    flexRender,
    ColumnDef,
} from '@tanstack/react-table';
import { cn, handleDomainFeedback } from '@/lib/utils';

import {
    Table,
    TableHeader,
    TableBody,
    TableHead,
    TableRow,
    TableCell,
} from '@/components/ui/table';
import {
    Pagination,
    PaginationContent,
    PaginationItem,
} from '@/components/ui/pagination';
import { Button } from '@/components/ui/button';
import {
    Select,
    SelectContent,
    SelectItem,
    SelectTrigger,
    SelectValue,
} from '@/components/ui/select';
import { Label } from '@/components/ui/label';
import { Badge } from '@/components/ui/badge';
import { Input } from '@/components/ui/input';

const NEXT_PUBLIC_API_URL = process.env.NEXT_PUBLIC_API_URL;
const NEXT_PUBLIC_TOP_DOMAINS_ENDPOINT =
    process.env.NEXT_PUBLIC_TOP_DOMAINS_ENDPOINT;

type Domain = {
    domain: string;
    status: string;
    last_checked: string;
};

type ApiResponse = {
    domains: Domain[];
    total: number;
};

export default function TopDomains() {
    // State for remote data and loading
    const [data, setData] = useState<Domain[]>([]);
    const [loading, setLoading] = useState(true);
    const [domainFeedback, setDomainFeedback] = useState<
        Record<string, boolean>
    >({});

    // Pagination state (TanStack Table uses 0-indexed pages)
    const [pageIndex, setPageIndex] = useState(0);
    const [pageSize, setPageSize] = useState(10);
    const [totalCount, setTotalCount] = useState(0);

    // Global filter (search input)
    const [globalFilter, setGlobalFilter] = useState('');

    // Sorting state: sort by and sort order.
    // Options for sortBy: "upvotes" (default), "alphabet", "length"
    // Options for sortOrder: "asc" or "desc"
    const [sortBy, setSortBy] = useState('upvotes');
    const [sortOrder, setSortOrder] = useState('desc');

    // Define your table columns.
    const columns = useMemo<ColumnDef<Domain>[]>(
        () => [
            {
                accessorKey: 'domain',
                header: () => <div className="text-left mr-auto">Domain</div>,
                enableSorting: true,
                cell: ({ getValue }) => (
                    <Link
                        href={`https://${getValue<string>()}`}
                        className="hover:underline text-left"
                    >
                        {getValue<string>()}
                    </Link>
                ),
            },
            {
                accessorKey: 'last_checked',
                header: () => <div className="text-center">Last Checked</div>,
                enableSorting: true,
                cell: ({ getValue }) => (
                    <div className="text-center">
                        {new Date(getValue<string>()).toLocaleDateString()}
                    </div>
                ),
            },
            {
                accessorKey: 'status',
                header: 'Status',
                cell: ({ getValue }) => {
                    const status = getValue<string>();
                    return (
                        <div className="justify-center flex">
                            <Badge
                                variant={
                                    status === 'free' ? 'default' : 'outline'
                                }
                                color={status === 'free' ? 'green' : 'red'}
                            >
                                {status === 'free' ? 'Available' : 'Taken'}
                            </Badge>
                        </div>
                    );
                },
            },
            {
                id: 'feedback',
                header: () => <div className="text-right">Feedback</div>,
                cell: ({ row }) => {
                    const domain = row.original.domain;
                    return (
                        <div className="flex justify-end gap-2 mr-4">
                            <button
                                className={cn(
                                    domainFeedback[domain] === true
                                        ? 'text-green-500'
                                        : 'text-neutral-500 hover:text-black'
                                )}
                                onClick={() =>
                                    handleDomainFeedback(
                                        domain,
                                        true,
                                        setDomainFeedback
                                    )
                                }
                            >
                                <ThumbsUp size={14} strokeWidth={1.5} />
                            </button>
                            <button
                                className={cn(
                                    domainFeedback[domain] === false
                                        ? 'text-red-500'
                                        : 'text-neutral-500 hover:text-black'
                                )}
                                onClick={() =>
                                    handleDomainFeedback(
                                        domain,
                                        false,
                                        setDomainFeedback
                                    )
                                }
                            >
                                <ThumbsDown size={14} strokeWidth={1.5} />
                            </button>
                        </div>
                    );
                },
            },
        ],
        [domainFeedback]
    );

    // Create the TanStack Table instance.
    const table = useReactTable({
        data,
        columns,
        manualPagination: true,
        pageCount: Math.ceil(totalCount / pageSize),
        state: {
            pagination: { pageIndex, pageSize },
            globalFilter,
        },
        onPaginationChange: (updater) => {
            const newPagination =
                typeof updater === 'function'
                    ? updater({ pageIndex, pageSize })
                    : updater;
            setPageIndex(newPagination.pageIndex);
            setPageSize(newPagination.pageSize);
        },
        getCoreRowModel: getCoreRowModel(),
        getPaginationRowModel: getPaginationRowModel(),
    });

    // Fetch data whenever pageIndex, pageSize, globalFilter, sortBy, or sortOrder changes.
    useEffect(() => {
        setLoading(true);
        const params = new URLSearchParams();
        params.append('page', (pageIndex + 1).toString());
        params.append('per_page', pageSize.toString());
        if (globalFilter) {
            params.append('filter', globalFilter);
        }
        if (sortBy) {
            params.append('sort_by', sortBy);
            params.append('sort_order', sortOrder);
        }
        fetch(
            `${NEXT_PUBLIC_API_URL}/${NEXT_PUBLIC_TOP_DOMAINS_ENDPOINT}?${params.toString()}`
        )
            .then((res) => res.json())
            .then((json: ApiResponse) => {
                setData(json.domains);
                setTotalCount(json.total);
                setLoading(false);
            })
            .catch((err) => {
                console.error('Error fetching domains:', err);
                setLoading(false);
            });
    }, [pageIndex, pageSize, globalFilter, sortBy, sortOrder]);

    const id = 'top-domains-select';

    return (
        <main className="flex flex-col items-center pt-24 min-h-[75vh] transition-all duration-300">
            <div className="w-full max-w-3xl space-y-6 transition-all duration-1000 pb-6">
                <h1 className="text-4xl font-semibold text-center tracking-tight flex flex-col">
                    <span>Explore and get Inspired by</span>
                    <span>the Top Rated Domains that are still available</span>
                </h1>
                <Input
                    type="text"
                    placeholder="Search domains..."
                    value={globalFilter}
                    onChange={(e) => {
                        setGlobalFilter(e.target.value);
                        setPageIndex(0); // Reset to first page on new search.
                    }}
                    className="w-full max-w-md mx-auto"
                />
            </div>
            {loading ? (
                <svg
                    width="14"
                    height="14"
                    viewBox="0 0 24 14"
                    xmlns="http://www.w3.org/2000/svg"
                >
                    <circle cx="4" cy="12" r="3">
                        <animate
                            id="spinner_qFRN"
                            begin="0;spinner_OcgL.end+0.25s"
                            attributeName="cy"
                            calcMode="spline"
                            dur="0.6s"
                            values="12;6;12"
                            keySplines=".33,.66,.66,1;.33,0,.66,.33"
                        />
                    </circle>
                    <circle cx="12" cy="12" r="3">
                        <animate
                            begin="spinner_qFRN.begin+0.1s"
                            attributeName="cy"
                            calcMode="spline"
                            dur="0.6s"
                            values="12;6;12"
                            keySplines=".33,.66,.66,1;.33,0,.66,.33"
                        />
                    </circle>
                    <circle cx="20" cy="12" r="3">
                        <animate
                            id="spinner_OcgL"
                            begin="spinner_qFRN.begin+0.2s"
                            attributeName="cy"
                            calcMode="spline"
                            dur="0.6s"
                            values="12;6;12"
                            keySplines=".33,.66,.66,1;.33,0,.66,.33"
                        />
                    </circle>
                </svg>
            ) : (
                <div className="mt-12 bg-white z-10 w-full max-w-4xl px-4 lg:px-0">
                    <Table className="table-fixed">
                        <TableHeader>
                            {table.getHeaderGroups().map((headerGroup) => (
                                <TableRow
                                    key={headerGroup.id}
                                    className="hover:bg-transparent"
                                >
                                    {headerGroup.headers.map((header) => (
                                        <TableHead
                                            key={header.id}
                                            style={{
                                                width: `${header.getSize()}px`,
                                            }}
                                            className="h-11"
                                        >
                                            {header.isPlaceholder ? null : header.column.getCanSort() ? (
                                                <div
                                                    className={cn(
                                                        header.column.getCanSort() &&
                                                            'flex h-full cursor-pointer select-none items-center justify-center gap-2'
                                                    )}
                                                    onClick={header.column.getToggleSortingHandler()}
                                                    onKeyDown={(e) => {
                                                        if (
                                                            header.column.getCanSort() &&
                                                            (e.key ===
                                                                'Enter' ||
                                                                e.key === ' ')
                                                        ) {
                                                            e.preventDefault();
                                                            header.column.getToggleSortingHandler()?.(
                                                                e
                                                            );
                                                        }
                                                    }}
                                                    tabIndex={
                                                        header.column.getCanSort()
                                                            ? 0
                                                            : undefined
                                                    }
                                                >
                                                    {flexRender(
                                                        header.column.columnDef
                                                            .header,
                                                        header.getContext()
                                                    )}
                                                    {{
                                                        asc: (
                                                            <ChevronUp
                                                                className="shrink-0 opacity-60"
                                                                size={16}
                                                                strokeWidth={2}
                                                                aria-hidden="true"
                                                            />
                                                        ),
                                                        desc: (
                                                            <ChevronDown
                                                                className="shrink-0 opacity-60"
                                                                size={16}
                                                                strokeWidth={2}
                                                                aria-hidden="true"
                                                            />
                                                        ),
                                                    }[
                                                        header.column.getIsSorted() as string
                                                    ] ?? null}
                                                </div>
                                            ) : (
                                                flexRender(
                                                    header.column.columnDef
                                                        .header,
                                                    header.getContext()
                                                )
                                            )}
                                        </TableHead>
                                    ))}
                                </TableRow>
                            ))}
                        </TableHeader>
                        <TableBody>
                            {table.getRowModel().rows?.length ? (
                                table.getRowModel().rows.map((row) => (
                                    <TableRow
                                        key={row.id}
                                        data-state={
                                            row.getIsSelected() && 'selected'
                                        }
                                    >
                                        {row.getVisibleCells().map((cell) => (
                                            <TableCell key={cell.id}>
                                                {flexRender(
                                                    cell.column.columnDef.cell,
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
                    <div className="flex items-center justify-between gap-8 p-2">
                        {/* Results per page */}
                        <div className="flex items-center gap-3">
                            <Label htmlFor={id} className="max-sm:sr-only">
                                Rows per page
                            </Label>
                            <Select
                                value={pageSize.toString()}
                                onValueChange={(value) => {
                                    setPageSize(Number(value));
                                    setPageIndex(0);
                                }}
                            >
                                <SelectTrigger
                                    id={id}
                                    className="w-fit whitespace-nowrap"
                                >
                                    <SelectValue placeholder="Select number of results" />
                                </SelectTrigger>
                                <SelectContent className="[&_*[role=option]>span]:end-2 [&_*[role=option]>span]:start-auto [&_*[role=option]]:pe-8 [&_*[role=option]]:ps-2">
                                    {[10, 20, 50].map((size) => (
                                        <SelectItem
                                            key={size}
                                            value={size.toString()}
                                        >
                                            Show {size}
                                        </SelectItem>
                                    ))}
                                </SelectContent>
                            </Select>
                        </div>
                        {/* Page number information */}
                        <div className="flex grow justify-end whitespace-nowrap text-sm text-muted-foreground">
                            <p
                                className="whitespace-nowrap text-sm text-muted-foreground"
                                aria-live="polite"
                            >
                                <span className="text-foreground">
                                    {pageIndex * pageSize + 1}-
                                    {Math.min(
                                        pageIndex * pageSize + pageSize,
                                        totalCount
                                    )}
                                </span>{' '}
                                of{' '}
                                <span className="text-foreground">
                                    {totalCount}
                                </span>
                            </p>
                        </div>
                        {/* Pagination buttons */}
                        <div>
                            <Pagination>
                                <PaginationContent>
                                    <PaginationItem>
                                        <Button
                                            size="icon"
                                            variant="outline"
                                            onClick={() => table.previousPage()}
                                            disabled={
                                                !table.getCanPreviousPage()
                                            }
                                            aria-label="Go to previous page"
                                        >
                                            <ChevronLeft
                                                size={16}
                                                strokeWidth={2}
                                                aria-hidden="true"
                                            />
                                        </Button>
                                    </PaginationItem>
                                    <PaginationItem>
                                        <Button
                                            size="icon"
                                            variant="outline"
                                            onClick={() => table.nextPage()}
                                            disabled={!table.getCanNextPage()}
                                            aria-label="Go to next page"
                                        >
                                            <ChevronRight
                                                size={16}
                                                strokeWidth={2}
                                                aria-hidden="true"
                                            />
                                        </Button>
                                    </PaginationItem>
                                </PaginationContent>
                            </Pagination>
                        </div>
                    </div>
                </div>
            )}
        </main>
    );
}

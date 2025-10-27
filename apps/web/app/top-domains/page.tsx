'use client';

import React, { useEffect, useMemo, useState } from 'react';
import {
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
import { cn, handleDomainFeedback, DomainFeedback } from '@/lib/utils';

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
const NEXT_PUBLIC_TOP_DOMAINS_ENDPOINT = 'v2/top_domains'; // Updated to v2

type Domain = {
    domain: string;
    status: string;
    last_checked: string;
    rating: number; // Added from RatedDomainsResponse
};

type ApiResponse = {
    domains: Domain[];
    total: number;
};

export default function TopDomains() {
    const [data, setData] = useState<Domain[]>([]);
    const [loading, setLoading] = useState(true);
    const [domainFeedback, setDomainFeedback] = useState<DomainFeedback>({});

    const [pageIndex, setPageIndex] = useState(0);
    const [pageSize, setPageSize] = useState(10);
    const [totalCount, setTotalCount] = useState(0);
    const [globalFilter, setGlobalFilter] = useState('');

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
                accessorKey: 'rating',
                header: () => <div className="text-center">User Rating</div>,
                enableSorting: true,
                cell: ({ getValue }) => (
                    <div className="text-center">
                        {getValue<number>().toFixed(1)}
                    </div>
                ),
            },
            {
                id: 'feedback',
                header: () => <div className="text-right">Rate</div>,
                cell: ({ row }) => {
                    const domain = row.original.domain;
                    const feedback = domainFeedback[domain];
                    return (
                        <div className="flex justify-end gap-1 mr-4 items-end">
                            <span className="text-xs text-gray-600 leading-none">
                                1
                            </span>
                            <div className="flex gap-[2px] items-end">
                                {Array.from(
                                    { length: 10 },
                                    (_, i) => i + 1
                                ).map((rating) => (
                                    <div
                                        key={rating}
                                        className={
                                            'w-1 rounded-t-sm cursor-pointer transition-all duration-200 ' +
                                            (feedback === rating
                                                ? 'h-4 bg-blue-500'
                                                : 'h-2 bg-gray-400 hover:h-3 hover:bg-gray-500')
                                        }
                                        onClick={() => {
                                            handleDomainFeedback(
                                                domain,
                                                rating,
                                                setDomainFeedback
                                            );
                                        }}
                                    />
                                ))}
                            </div>
                            <span className="text-xs text-gray-600 leading-none">
                                10
                            </span>
                        </div>
                    );
                },
            },
        ],
        [domainFeedback]
    );

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

    useEffect(() => {
        setLoading(true);
        const params = new URLSearchParams();
        params.append('page', (pageIndex + 1).toString()); // API uses 1-indexed pages
        params.append('per_page', pageSize.toString());
        if (globalFilter) {
            params.append('filter', globalFilter);
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
    }, [pageIndex, pageSize, globalFilter]);

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
                        setPageIndex(0);
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

'use client';

import { useSession } from '@/lib/auth-client';
import { cn } from '@/lib/utils';
import { useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import {
    MetricsSummaryResponse,
    MetricsHistoryResponse,
    MetricsQueueResponse,
    MetricsWorkerResponse,
    WorkerStat,
} from '@/lib/types';
import { Card } from '@/components/ui/card';
import {
    Select,
    SelectContent,
    SelectItem,
    SelectTrigger,
    SelectValue,
} from '@/components/ui/select';
import { Collapsible } from '@/components/ui/collapsible';
import {
    Area,
    AreaChart,
    ResponsiveContainer,
    Tooltip,
    XAxis,
    YAxis,
    Bar,
    BarChart,
    Line,
    LineChart,
    ComposedChart,
    Legend,
} from 'recharts';
import { motion } from 'motion/react';
import {
    Activity,
    Zap,
    AlertCircle,
    CheckCircle,
    Clock,
    Layers,
    Database,
    RefreshCw,
    Cpu,
} from 'lucide-react';

import { PageShell, PageHeader } from '@/components/page-layout';

const API_URL = process.env.NEXT_PUBLIC_API_URL;

const COLORS = {
    pink: '#e59999',
    purple: '#9683dd',
    cyan: '#8fdadb',
    blue: '#3957c0',
    indigo: '#6366f1',
    red: '#ef4444',
    success: '#10b981',
    orange: '#f97316',
    teal: '#14b8a6',
    yellow: '#eab308',
};

export default function Dashboard() {
    const { data: session, isPending } = useSession();
    const router = useRouter();
    const [isCheckingAccess, setIsCheckingAccess] = useState(true);
    const [timeRange, setTimeRange] = useState<'1h' | '24h' | 'all'>('1h');
    const [summary24h, setSummary24h] = useState<MetricsSummaryResponse | null>(
        null
    );
    const [summaryAll, setSummaryAll] = useState<MetricsSummaryResponse | null>(
        null
    );
    const [history, setHistory] = useState<MetricsHistoryResponse | null>(null);
    const [queueData, setQueueData] = useState<MetricsQueueResponse | null>(
        null
    );
    const [workerData, setWorkerData] = useState<MetricsWorkerResponse | null>(
        null
    );

    const [isLoadingSummary, setIsLoadingSummary] = useState(true);
    const [isLoadingHistory, setIsLoadingHistory] = useState(true);
    const [isLoadingQueue, setIsLoadingQueue] = useState(true);
    const [isLoadingWorkers, setIsLoadingWorkers] = useState(true);
    const [error, setError] = useState<string | null>(null);

    // Derived data
    const formattedChartData = history?.chart_data?.map((point) => ({
        ...point,
        avg_latency: point.avg_latency / 1000,
        p99_latency: point.p99_latency / 1000,
        avg_generation_time: point.avg_generation_time / 1000,
        avg_check_time: point.avg_check_time / 1000,
        avg_success_rate: point.avg_success_rate * 100,
        cache_hit_rate: point.cache_hit_rate * 100,
    }));

    const formattedQueueHistory =
        queueData?.queue_history?.map((point) => ({
            ...point,
            timestamp: new Date(point.timestamp).getTime(),
            dateStr: new Date(point.timestamp).toLocaleTimeString(),
        })) || [];

    useEffect(() => {
        if (!isPending && !session?.user) {
            router.push('/login');
            return;
        }

        if (session?.user) {
            setIsCheckingAccess(false);
        }
    }, [session, isPending, router]);

    // Fetch Functions
    useEffect(() => {
        if (!isCheckingAccess && session?.user) {
            const fetchAll = () => {
                setError(null);
                // Summary
                setIsLoadingSummary(true);
                Promise.all([
                    fetch(`${API_URL}/v1/metrics/summary?range=24h`).then(
                        (res) => {
                            if (!res.ok)
                                throw new Error(
                                    `Summary 24h: ${res.statusText}`
                                );
                            return res.json();
                        }
                    ),
                    fetch(`${API_URL}/v1/metrics/summary?range=all`).then(
                        (res) => {
                            if (!res.ok)
                                throw new Error(
                                    `Summary All: ${res.statusText}`
                                );
                            return res.json();
                        }
                    ),
                ])
                    .then(([data24h, dataAll]) => {
                        setSummary24h(data24h);
                        setSummaryAll(dataAll);
                    })
                    .catch((err) => {
                        console.error('Summary fetch error', err);
                        setError((prev) => prev || err.message);
                    })
                    .finally(() => setIsLoadingSummary(false));

                // History
                setIsLoadingHistory(true);
                fetch(`${API_URL}/v1/metrics/history?range=${timeRange}`)
                    .then((res) => {
                        if (!res.ok)
                            throw new Error(`History: ${res.statusText}`);
                        return res.json();
                    })
                    .then((data) => setHistory(data))
                    .catch((err) => {
                        console.error('History fetch error', err);
                        setError((prev) => prev || err.message);
                    })
                    .finally(() => setIsLoadingHistory(false));

                // Queue
                const queueRange = timeRange === '1h' ? '1h' : '24h';
                setIsLoadingQueue(true);
                fetch(`${API_URL}/v1/metrics/queue?range=${queueRange}`)
                    .then((res) => {
                        if (!res.ok)
                            throw new Error(`Queue: ${res.statusText}`);
                        return res.json();
                    })
                    .then((data) => setQueueData(data))
                    .catch((err) => {
                        console.error('Queue fetch error', err);
                    })
                    .finally(() => setIsLoadingQueue(false));

                // Workers
                setIsLoadingWorkers(true);
                fetch(`${API_URL}/v1/metrics/workers`)
                    .then((res) => {
                        if (!res.ok)
                            throw new Error(`Workers: ${res.statusText}`);
                        return res.json();
                    })
                    .then((data) => setWorkerData(data))
                    .catch((err) => {
                        console.error('Workers fetch error', err);
                    })
                    .finally(() => setIsLoadingWorkers(false));
            };

            fetchAll();
        }
    }, [isCheckingAccess, session, timeRange]);

    if (isPending || isCheckingAccess) {
        return (
            <div className="flex flex-col items-center justify-center min-h-[80vh]">
                <div className="w-8 h-8 border-2 border-primary border-t-transparent rounded-full animate-spin" />
            </div>
        );
    }

    if (!session?.user) {
        return null;
    }

    return (
        <PageShell>
            <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 mb-8">
                <PageHeader
                    title="Overview"
                    description="System performance and usage metrics."
                    className="mb-0"
                />
                <div className="flex items-center gap-2">
                    <span className="text-sm text-muted-foreground hidden sm:inline-block no-wrap">
                        Time Range:
                    </span>
                    <Select
                        value={timeRange}
                        onValueChange={(val) =>
                            setTimeRange(val as '1h' | '24h' | 'all')
                        }
                    >
                        <SelectTrigger className="w-[180px]">
                            <SelectValue placeholder="Select range" />
                        </SelectTrigger>
                        <SelectContent>
                            <SelectItem value="1h">Last 1 Hour</SelectItem>
                            <SelectItem value="24h">Last 24 Hours</SelectItem>
                            <SelectItem value="all">All Time</SelectItem>
                        </SelectContent>
                    </Select>
                </div>
            </div>

            <div className="w-full max-w-6xl xl:w-[1152px] space-y-12">
                {error && (
                    <div className="bg-destructive/10 border border-destructive/20 text-destructive p-4 rounded-lg flex items-center gap-2">
                        <AlertCircle className="w-4 h-4" />
                        <p className="text-sm font-medium">
                            Error loading metrics: {error}. Please check server
                            logs or database migrations.
                        </p>
                    </div>
                )}
                {/* Primary Stats */}
                {isLoadingSummary ? (
                    <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-6 animate-pulse">
                        {[...Array(4)].map((_, i) => (
                            <div
                                key={i}
                                className="h-32 bg-muted/50 rounded-xl"
                            />
                        ))}
                    </div>
                ) : summaryAll && summary24h ? (
                    <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-6">
                        <StatsCard
                            icon={<Activity className="w-4 h-4" />}
                            label="Total Suggestions"
                            value={summaryAll.total_suggestions.toLocaleString()}
                            subValue={`${summary24h.total_suggestions.toLocaleString()} in last 24h`}
                            delay={0.1}
                        />
                        <StatsCard
                            icon={<Layers className="w-4 h-4" />}
                            label="Generated Domains"
                            value={summaryAll.total_generated_domains.toLocaleString()}
                            subValue={`${summary24h.total_generated_domains.toLocaleString()} in last 24h`}
                            delay={0.2}
                        />
                        <StatsCard
                            icon={<Clock className="w-4 h-4" />}
                            label="Avg Latency"
                            value={`${(
                                summaryAll.avg_latency_ms / 1000
                            ).toFixed(2)}s`}
                            subValue={`${(
                                summary24h.avg_latency_ms / 1000
                            ).toFixed(2)}s in last 24h`}
                            delay={0.3}
                        />
                        <StatsCard
                            icon={<CheckCircle className="w-4 h-4" />}
                            label="Success Rate"
                            value={`${(
                                summaryAll.avg_success_rate * 100
                            ).toFixed(1)}%`}
                            subValue={`${(
                                summary24h.avg_success_rate * 100
                            ).toFixed(1)}% in last 24h`}
                            delay={0.4}
                        />
                    </div>
                ) : null}

                {/* Charts Grid */}
                <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
                    {/* Latency Chart */}
                    <ChartCard
                        title="Latency Trends"
                        delay={0.5}
                        isLoading={isLoadingHistory}
                    >
                        {formattedChartData && (
                            <ResponsiveContainer width="100%" height="100%">
                                <LineChart
                                    data={formattedChartData}
                                    margin={{
                                        top: 10,
                                        right: 10,
                                        left: -20,
                                        bottom: 0,
                                    }}
                                >
                                    <XAxis
                                        dataKey="date"
                                        axisLine={false}
                                        tickLine={false}
                                        tick={{
                                            fontSize: 12,
                                            fill: 'hsl(var(--muted-foreground))',
                                        }}
                                        tickFormatter={(value) =>
                                            formatXAxisDate(value, timeRange)
                                        }
                                        minTickGap={30}
                                    />
                                    <YAxis
                                        axisLine={false}
                                        tickLine={false}
                                        tick={{
                                            fontSize: 12,
                                            fill: 'hsl(var(--muted-foreground))',
                                        }}
                                        width={50}
                                        unit="s"
                                    />
                                    <Tooltip
                                        content={<CustomTooltip />}
                                        cursor={{
                                            stroke: 'hsl(var(--border))',
                                            strokeWidth: 1,
                                            strokeDasharray: '4 4',
                                        }}
                                    />
                                    <Legend />
                                    <Line
                                        type="monotone"
                                        dataKey="p99_latency"
                                        stroke={COLORS.purple}
                                        name="P99"
                                        strokeWidth={2}
                                        dot={false}
                                        activeDot={{ r: 4, strokeWidth: 0 }}
                                        strokeOpacity={0.7}
                                    />
                                    <Line
                                        type="monotone"
                                        dataKey="avg_latency"
                                        stroke={COLORS.blue}
                                        name="Avg"
                                        strokeWidth={2}
                                        dot={false}
                                        activeDot={{ r: 4, strokeWidth: 0 }}
                                    />
                                </LineChart>
                            </ResponsiveContainer>
                        )}
                    </ChartCard>

                    {/* Processing Speed */}
                    <ChartCard
                        title="Processing Speed"
                        delay={0.6}
                        isLoading={isLoadingHistory}
                    >
                        {formattedChartData && (
                            <ResponsiveContainer width="100%" height="100%">
                                <AreaChart
                                    data={formattedChartData}
                                    margin={{
                                        top: 10,
                                        right: 10,
                                        left: -20,
                                        bottom: 0,
                                    }}
                                >
                                    <defs>
                                        <linearGradient
                                            id="colorGen"
                                            x1="0"
                                            y1="0"
                                            x2="0"
                                            y2="1"
                                        >
                                            <stop
                                                offset="5%"
                                                stopColor={COLORS.purple}
                                                stopOpacity={0.3}
                                            />
                                            <stop
                                                offset="95%"
                                                stopColor={COLORS.purple}
                                                stopOpacity={0}
                                            />
                                        </linearGradient>
                                        <linearGradient
                                            id="colorCheck"
                                            x1="0"
                                            y1="0"
                                            x2="0"
                                            y2="1"
                                        >
                                            <stop
                                                offset="5%"
                                                stopColor={COLORS.cyan}
                                                stopOpacity={0.3}
                                            />
                                            <stop
                                                offset="95%"
                                                stopColor={COLORS.cyan}
                                                stopOpacity={0}
                                            />
                                        </linearGradient>
                                    </defs>
                                    <XAxis
                                        dataKey="date"
                                        axisLine={false}
                                        tickLine={false}
                                        tick={{
                                            fontSize: 12,
                                            fill: 'hsl(var(--muted-foreground))',
                                        }}
                                        tickFormatter={(value) =>
                                            formatXAxisDate(value, timeRange)
                                        }
                                        minTickGap={30}
                                    />
                                    <YAxis
                                        axisLine={false}
                                        tickLine={false}
                                        tick={{
                                            fontSize: 12,
                                            fill: 'hsl(var(--muted-foreground))',
                                        }}
                                        width={50}
                                        unit="ms"
                                    />
                                    <Tooltip
                                        content={<CustomTooltip />}
                                        cursor={{
                                            stroke: 'hsl(var(--border))',
                                            strokeWidth: 1,
                                            strokeDasharray: '4 4',
                                        }}
                                    />
                                    <Legend />
                                    <Area
                                        type="monotone"
                                        dataKey="avg_generation_time"
                                        name="Generation"
                                        stackId="1"
                                        stroke={COLORS.purple}
                                        fill="url(#colorGen)"
                                        strokeWidth={2}
                                    />
                                    <Area
                                        type="monotone"
                                        dataKey="avg_check_time"
                                        name="Check"
                                        stackId="1"
                                        stroke={COLORS.cyan}
                                        fill="url(#colorCheck)"
                                        strokeWidth={2}
                                    />
                                </AreaChart>
                            </ResponsiveContainer>
                        )}
                    </ChartCard>

                    {/* Yield & Success */}
                    <ChartCard
                        title="Yield & Success"
                        delay={0.65}
                        isLoading={isLoadingHistory}
                    >
                        {formattedChartData && (
                            <ResponsiveContainer width="100%" height="100%">
                                <ComposedChart
                                    data={formattedChartData}
                                    margin={{
                                        top: 10,
                                        right: 10,
                                        left: -20,
                                        bottom: 0,
                                    }}
                                >
                                    <XAxis
                                        dataKey="date"
                                        axisLine={false}
                                        tickLine={false}
                                        tick={{
                                            fontSize: 12,
                                            fill: 'hsl(var(--muted-foreground))',
                                        }}
                                        tickFormatter={(value) =>
                                            formatXAxisDate(value, timeRange)
                                        }
                                        minTickGap={30}
                                    />
                                    <YAxis
                                        yAxisId="left"
                                        axisLine={false}
                                        tickLine={false}
                                        tick={{
                                            fontSize: 12,
                                            fill: 'hsl(var(--muted-foreground))',
                                        }}
                                        width={40}
                                    />
                                    <YAxis
                                        yAxisId="right"
                                        orientation="right"
                                        axisLine={false}
                                        tickLine={false}
                                        tick={{
                                            fontSize: 12,
                                            fill: 'hsl(var(--muted-foreground))',
                                        }}
                                        unit="%"
                                        width={50}
                                    />
                                    <Tooltip
                                        content={<CustomTooltip />}
                                        cursor={{
                                            fill: 'hsl(var(--muted))',
                                            opacity: 0.2,
                                        }}
                                    />
                                    <Bar
                                        yAxisId="left"
                                        dataKey="avg_yield"
                                        name="Yield"
                                        fill={COLORS.blue}
                                        radius={[4, 4, 0, 0]}
                                        barSize={32}
                                    />
                                    <Line
                                        yAxisId="right"
                                        type="monotone"
                                        dataKey="avg_success_rate"
                                        name="Success Rate"
                                        stroke={COLORS.purple}
                                        strokeWidth={2}
                                        dot={false}
                                    />
                                </ComposedChart>
                            </ResponsiveContainer>
                        )}
                    </ChartCard>

                    {/* Reliability & Caching */}
                    <ChartCard
                        title="Reliability & Caching"
                        delay={0.7}
                        isLoading={isLoadingHistory}
                    >
                        {formattedChartData && (
                            <ResponsiveContainer width="100%" height="100%">
                                <ComposedChart
                                    data={formattedChartData}
                                    margin={{
                                        top: 10,
                                        right: 10,
                                        left: -20,
                                        bottom: 0,
                                    }}
                                >
                                    <XAxis
                                        dataKey="date"
                                        axisLine={false}
                                        tickLine={false}
                                        tick={{
                                            fontSize: 12,
                                            fill: 'hsl(var(--muted-foreground))',
                                        }}
                                        tickFormatter={(value) =>
                                            formatXAxisDate(value, timeRange)
                                        }
                                        minTickGap={30}
                                    />
                                    <YAxis
                                        yAxisId="left"
                                        axisLine={false}
                                        tickLine={false}
                                        tick={{
                                            fontSize: 12,
                                            fill: 'hsl(var(--muted-foreground))',
                                        }}
                                        width={40}
                                        unit="%"
                                    />
                                    <YAxis
                                        yAxisId="right"
                                        orientation="right"
                                        axisLine={false}
                                        tickLine={false}
                                        tick={{
                                            fontSize: 12,
                                            fill: 'hsl(var(--muted-foreground))',
                                        }}
                                        width={40}
                                    />
                                    <Tooltip
                                        content={<CustomTooltip />}
                                        cursor={{
                                            fill: 'hsl(var(--muted))',
                                            opacity: 0.2,
                                        }}
                                    />
                                    <Legend />
                                    <Area
                                        yAxisId="left"
                                        type="monotone"
                                        dataKey="cache_hit_rate"
                                        name="Cache Hit Rate"
                                        fill={COLORS.cyan}
                                        fillOpacity={0.2}
                                        stroke={COLORS.cyan}
                                        strokeWidth={2}
                                    />
                                    <Line
                                        yAxisId="right"
                                        type="monotone"
                                        dataKey="retry_rate"
                                        name="Avg Retries"
                                        stroke={COLORS.pink}
                                        strokeWidth={2}
                                        dot={false}
                                    />
                                </ComposedChart>
                            </ResponsiveContainer>
                        )}
                    </ChartCard>

                    {/* Worker Distribution */}
                    <ChartCard
                        title="Worker Performance"
                        delay={0.75}
                        isLoading={isLoadingQueue || isLoadingWorkers}
                    >
                        {queueData && workerData && (
                            <div className="flex flex-col h-full gap-4">
                                <div className="flex-1 min-h-0">
                                    <h4 className="text-sm font-medium mb-2 text-muted-foreground">
                                        Processing Time per Worker
                                    </h4>
                                    <ResponsiveContainer
                                        width="100%"
                                        height="80%"
                                    >
                                        <BarChart
                                            data={
                                                workerData.worker_stats
                                                    ?.filter((w) => w.is_active)
                                                    .map((w) => ({
                                                        name: w.worker_id
                                                            .split(':')
                                                            .pop(),
                                                        processing:
                                                            w.avg_processing_time_ms,
                                                        jobs: w.jobs_processed,
                                                    })) || []
                                            }
                                            margin={{
                                                top: 5,
                                                right: 10,
                                                left: -20,
                                                bottom: 0,
                                            }}
                                        >
                                            <XAxis
                                                dataKey="name"
                                                axisLine={false}
                                                tickLine={false}
                                                tick={{
                                                    fontSize: 12,
                                                    fill: 'hsl(var(--muted-foreground))',
                                                }}
                                            />
                                            <YAxis
                                                axisLine={false}
                                                tickLine={false}
                                                tick={{
                                                    fontSize: 12,
                                                    fill: 'hsl(var(--muted-foreground))',
                                                }}
                                                width={50}
                                                unit="ms"
                                            />
                                            <Tooltip
                                                content={<WorkerTooltip />}
                                            />
                                            <Bar
                                                dataKey="processing"
                                                name="Avg Processing Time"
                                                fill={COLORS.purple}
                                                radius={[4, 4, 0, 0]}
                                            />
                                        </BarChart>
                                    </ResponsiveContainer>
                                </div>
                                <div className="flex items-center justify-between border-t border-border pt-4">
                                    <div className="flex items-center gap-6">
                                        <div className="flex flex-col">
                                            <span className="text-xs text-muted-foreground">
                                                Queue
                                            </span>
                                            <span className="text-xl font-bold font-mono">
                                                {queueData.queue_length}
                                            </span>
                                        </div>
                                        <div className="flex flex-col">
                                            <span className="text-xs text-muted-foreground">
                                                Active Workers
                                            </span>
                                            <span className="text-xl font-bold font-mono">
                                                <span className="text-green-500">
                                                    {workerData.active_workers ||
                                                        0}
                                                </span>
                                                <span className="text-muted-foreground text-sm">
                                                    /
                                                    {workerData.total_workers ||
                                                        0}
                                                </span>
                                            </span>
                                        </div>
                                        <div className="flex flex-col">
                                            <span className="text-xs text-muted-foreground">
                                                Avg Processing
                                            </span>
                                            <span className="text-xl font-bold font-mono">
                                                {(
                                                    workerData.avg_processing_time_ms ||
                                                    0
                                                ).toFixed(0)}
                                                ms
                                            </span>
                                        </div>
                                        <div className="flex flex-col">
                                            <span className="text-xs text-muted-foreground">
                                                Avg Queue Wait
                                            </span>
                                            <span className="text-xl font-bold font-mono">
                                                {(
                                                    queueData.avg_queue_wait_time_ms ||
                                                    0
                                                ).toFixed(0)}
                                                ms
                                            </span>
                                        </div>
                                    </div>
                                </div>
                            </div>
                        )}
                    </ChartCard>

                    {/* Queue Depth History */}
                    <ChartCard
                        title="Queue Depth Over Time"
                        delay={0.77}
                        isLoading={isLoadingQueue}
                    >
                        {formattedQueueHistory.length > 0 && (
                            <ResponsiveContainer width="100%" height="100%">
                                <AreaChart
                                    data={formattedQueueHistory}
                                    margin={{
                                        top: 10,
                                        right: 10,
                                        left: -20,
                                        bottom: 0,
                                    }}
                                >
                                    <defs>
                                        <linearGradient
                                            id="colorQueueDepth"
                                            x1="0"
                                            y1="0"
                                            x2="0"
                                            y2="1"
                                        >
                                            <stop
                                                offset="5%"
                                                stopColor={COLORS.orange}
                                                stopOpacity={0.4}
                                            />
                                            <stop
                                                offset="95%"
                                                stopColor={COLORS.orange}
                                                stopOpacity={0}
                                            />
                                        </linearGradient>
                                    </defs>
                                    <XAxis
                                        dataKey="timestamp"
                                        axisLine={false}
                                        tickLine={false}
                                        tick={{
                                            fontSize: 12,
                                            fill: 'hsl(var(--muted-foreground))',
                                        }}
                                        type="number"
                                        domain={['dataMin', 'dataMax']}
                                        tickFormatter={(value) =>
                                            new Date(value).toLocaleTimeString(
                                                undefined,
                                                {
                                                    hour: '2-digit',
                                                    minute: '2-digit',
                                                }
                                            )
                                        }
                                        minTickGap={40}
                                    />
                                    <YAxis
                                        axisLine={false}
                                        tickLine={false}
                                        tick={{
                                            fontSize: 12,
                                            fill: 'hsl(var(--muted-foreground))',
                                        }}
                                        width={40}
                                        allowDecimals={false}
                                    />
                                    <Tooltip content={<CustomTooltip />} />
                                    <Area
                                        type="stepAfter"
                                        dataKey="depth"
                                        name="Queue Depth"
                                        stroke={COLORS.orange}
                                        fill="url(#colorQueueDepth)"
                                        strokeWidth={2}
                                    />
                                </AreaChart>
                            </ResponsiveContainer>
                        )}
                    </ChartCard>

                    {/* Worker Stats Info Card - using data from worker endpoint */}
                    <div className="col-span-1 lg:col-span-2 flex flex-col gap-6">
                        {isLoadingWorkers ? (
                            <div className="h-24 bg-muted/50 rounded-xl animate-pulse w-full" />
                        ) : (
                            <>
                                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
                                    {(workerData?.worker_stats || [])
                                        .filter((w) => w.is_active)
                                        .map((worker, index) => (
                                            <WorkerCard
                                                key={worker.worker_id}
                                                worker={worker}
                                                delay={0.8 + index * 0.1}
                                            />
                                        ))}
                                </div>
                                {(workerData?.worker_stats || []).some(
                                    (w) => !w.is_active
                                ) && (
                                    <Collapsible
                                        title="Inactive Workers"
                                        count={
                                            (
                                                workerData?.worker_stats || []
                                            ).filter((w) => !w.is_active).length
                                        }
                                    >
                                        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
                                            {(workerData?.worker_stats || [])
                                                .filter((w) => !w.is_active)
                                                .map((worker, index) => (
                                                    <WorkerCard
                                                        key={worker.worker_id}
                                                        worker={worker}
                                                        delay={
                                                            0.8 +
                                                            (index +
                                                                ((
                                                                    workerData?.worker_stats ||
                                                                    []
                                                                ).filter(
                                                                    (w) =>
                                                                        w.is_active
                                                                ).length ||
                                                                    0)) *
                                                                0.1
                                                        }
                                                    />
                                                ))}
                                        </div>
                                    </Collapsible>
                                )}
                            </>
                        )}
                    </div>

                    {/* Resources & Errors */}
                    <ChartCard
                        title="Resources & Errors"
                        delay={0.8}
                        isLoading={isLoadingHistory}
                    >
                        {formattedChartData && (
                            <ResponsiveContainer width="100%" height="100%">
                                <ComposedChart
                                    data={formattedChartData}
                                    margin={{
                                        top: 10,
                                        right: 10,
                                        left: -20,
                                        bottom: 0,
                                    }}
                                >
                                    <XAxis
                                        dataKey="date"
                                        axisLine={false}
                                        tickLine={false}
                                        tick={{
                                            fontSize: 12,
                                            fill: 'hsl(var(--muted-foreground))',
                                        }}
                                        tickFormatter={(value) =>
                                            formatXAxisDate(value, timeRange)
                                        }
                                        minTickGap={30}
                                    />
                                    <YAxis
                                        yAxisId="left"
                                        axisLine={false}
                                        tickLine={false}
                                        tick={{
                                            fontSize: 12,
                                            fill: 'hsl(var(--muted-foreground))',
                                        }}
                                        width={40}
                                    />
                                    <YAxis
                                        yAxisId="right"
                                        orientation="right"
                                        axisLine={false}
                                        tickLine={false}
                                        tick={{
                                            fontSize: 12,
                                            fill: 'hsl(var(--destructive))',
                                        }}
                                        width={40}
                                    />
                                    <Tooltip content={<CustomTooltip />} />
                                    <Legend />
                                    <Area
                                        yAxisId="left"
                                        type="monotone"
                                        dataKey="avg_tokens"
                                        name="Avg Tokens"
                                        stroke={COLORS.purple}
                                        fill={COLORS.purple}
                                        fillOpacity={0.1}
                                        strokeWidth={2}
                                    />
                                    <Bar
                                        yAxisId="right"
                                        dataKey="error_count"
                                        name="Errors"
                                        fill={COLORS.red}
                                        radius={[4, 4, 0, 0]}
                                        barSize={32}
                                    />
                                </ComposedChart>
                            </ResponsiveContainer>
                        )}
                    </ChartCard>
                </div>

                {/* Secondary Stats */}
                {isLoadingSummary ? (
                    <div className="grid grid-cols-1 md:grid-cols-4 gap-6 animate-pulse">
                        {[...Array(4)].map((_, i) => (
                            <div
                                key={i}
                                className="h-24 bg-muted/50 rounded-xl"
                            />
                        ))}
                    </div>
                ) : summaryAll ? (
                    <div className="grid grid-cols-1 md:grid-cols-4 gap-6">
                        <StatsCard
                            icon={<Zap className="w-4 h-4" />}
                            label="Resource Usage"
                            value={Math.round(
                                summaryAll.avg_tokens_per_request || 0
                            ).toString()}
                            subValue={`${Math.round(
                                summary24h?.avg_tokens_per_request || 0
                            )} in last 24h`}
                            delay={0.9}
                            minimal
                        />
                        <StatsCard
                            icon={<Database className="w-4 h-4" />}
                            label="Cache Hit Rate"
                            value={`${(
                                (summaryAll.cache_hit_rate || 0) * 100
                            ).toFixed(1)}%`}
                            subValue={`${(
                                (summary24h?.cache_hit_rate || 0) * 100
                            ).toFixed(1)}% in last 24h`}
                            delay={1.0}
                            minimal
                        />
                        <StatsCard
                            icon={<RefreshCw className="w-4 h-4" />}
                            label="Avg Retries"
                            value={(summaryAll.avg_retry_count || 0).toFixed(2)}
                            subValue={`${(
                                summary24h?.avg_retry_count || 0
                            ).toFixed(2)} in last 24h`}
                            delay={1.1}
                            minimal
                        />
                        <StatsCard
                            icon={<AlertCircle className="w-4 h-4" />}
                            label="Total Errors"
                            value={(summaryAll.total_errors || 0).toString()}
                            subValue={`${
                                summary24h?.total_errors || 0
                            } in last 24h`}
                            delay={1.2}
                            minimal
                        />
                    </div>
                ) : null}
            </div>
        </PageShell>
    );
}

function StatsCard({
    icon,
    label,
    value,
    subValue,
    delay = 0,
    minimal = false,
}: {
    icon: React.ReactNode;
    label: string;
    value: string;
    subValue: string;
    delay?: number;
    minimal?: boolean;
}) {
    return (
        <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.5, delay }}
        >
            <Card
                className={cn(
                    'flex-col justify-between h-full hover:scale-[1.02] border-neutral-200'
                )}
            >
                <div className="flex items-center gap-2 text-muted-foreground mb-4">
                    <span className="p-2 bg-primary/5 rounded-lg text-primary">
                        {icon}
                    </span>
                    <h3 className="text-sm font-medium">{label}</h3>
                </div>
                <div>
                    <div className="text-3xl font-heading font-semibold tracking-tight text-foreground">
                        {value}
                    </div>
                    <p className="text-xs text-muted-foreground mt-1">
                        {subValue}
                    </p>
                </div>
            </Card>
        </motion.div>
    );
}

function WorkerCard({
    worker,
    delay = 0,
}: {
    worker: WorkerStat;
    delay?: number;
}) {
    const lastSeenDate = new Date(worker.last_seen);
    const timeAgo = getTimeAgo(lastSeenDate);

    return (
        <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.5, delay }}
        >
            <Card
                className={cn(
                    'flex-col justify-between h-full hover:scale-[1.02] border-neutral-200',
                    !worker.is_active && 'opacity-50'
                )}
            >
                <div className="flex items-center justify-between mb-4">
                    <div className="flex items-center gap-2 text-muted-foreground">
                        <span className="p-2 bg-primary/5 rounded-lg text-primary">
                            <Cpu className="w-4 h-4" />
                        </span>
                        <h3 className="text-sm font-medium">
                            Worker {worker.worker_id.split(':').pop()}
                        </h3>
                    </div>
                    <div
                        className={cn(
                            'w-2 h-2 rounded-full',
                            worker.is_active ? 'bg-green-500' : 'bg-gray-400'
                        )}
                        title={worker.is_active ? 'Active' : 'Inactive (>1h)'}
                    />
                </div>
                <div className="space-y-2">
                    <div className="flex justify-between items-center">
                        <span className="text-xs text-muted-foreground">
                            Share
                        </span>
                        <span className="text-lg font-heading font-semibold">
                            {worker.percentage}%
                        </span>
                    </div>
                    <div className="flex justify-between items-center">
                        <span className="text-xs text-muted-foreground">
                            Jobs
                        </span>
                        <span className="text-sm font-mono">
                            {worker.jobs_processed.toLocaleString()}
                        </span>
                    </div>
                    <div className="flex justify-between items-center">
                        <span className="text-xs text-muted-foreground">
                            Avg Time
                        </span>
                        <span className="text-sm font-mono">
                            {worker.avg_processing_time_ms.toFixed(0)}ms
                        </span>
                    </div>
                    <div className="flex justify-between items-center">
                        <span className="text-xs text-muted-foreground">
                            Last Seen
                        </span>
                        <span className="text-xs text-muted-foreground">
                            {timeAgo}
                        </span>
                    </div>
                </div>
            </Card>
        </motion.div>
    );
}

function getTimeAgo(date: Date): string {
    const seconds = Math.floor((new Date().getTime() - date.getTime()) / 1000);

    if (seconds < 60) return 'just now';
    if (seconds < 3600) return `${Math.floor(seconds / 60)}m ago`;
    if (seconds < 86400) return `${Math.floor(seconds / 3600)}h ago`;
    return `${Math.floor(seconds / 86400)}d ago`;
}

function ChartCard({
    title,
    children,
    delay = 0,
    isLoading = false,
}: {
    title: string;
    children: React.ReactNode;
    delay?: number;
    isLoading?: boolean;
}) {
    return (
        <motion.div
            initial={{ opacity: 0, scale: 0.95 }}
            animate={{ opacity: 1, scale: 1 }}
            transition={{ duration: 0.5, delay }}
            className="h-[350px] flex flex-col"
        >
            <Card className="h-full flex-col border-neutral-200">
                <h3 className="text-base font-medium mb-6 font-heading">
                    {title}
                </h3>
                <div className="flex-1 min-h-0 w-full relative">
                    {isLoading ? (
                        <div className="absolute inset-0 flex items-center justify-center bg-background/50 z-10">
                            <div className="w-6 h-6 border-2 border-primary border-t-transparent rounded-full animate-spin" />
                        </div>
                    ) : null}
                    {children}
                </div>
            </Card>
        </motion.div>
    );
}

function formatXAxisDate(value: string, range: '1h' | '24h' | 'all') {
    const date = new Date(value);
    if (range === '1h' || range === '24h') {
        return date.toLocaleTimeString(undefined, {
            hour: '2-digit',
            minute: '2-digit',
        });
    }
    return date.toLocaleDateString(undefined, {
        month: 'short',
        day: 'numeric',
    });
}

function WorkerTooltip({ active, payload, label }: any) {
    if (active && payload && payload.length) {
        return (
            <div className="bg-popover/95 backdrop-blur-sm border border-border p-3 rounded-lg shadow-lg text-xs">
                <p className="font-medium mb-2 text-popover-foreground">
                    Worker {label}
                </p>
                <div className="space-y-1">
                    {payload.map((entry: any, index: number) => (
                        <div key={index} className="flex items-center gap-2">
                            <div
                                className="w-2 h-2 rounded-full"
                                style={{
                                    backgroundColor: entry.fill || entry.color,
                                }}
                            />
                            <span className="text-muted-foreground">
                                {entry.name}:
                            </span>
                            <span className="font-mono font-medium text-foreground">
                                {entry.value.toFixed(0)}ms
                            </span>
                        </div>
                    ))}
                    {payload[0]?.payload?.jobs && (
                        <div className="flex items-center gap-2 pt-1 border-t border-border mt-1">
                            <span className="text-muted-foreground">Jobs:</span>
                            <span className="font-mono font-medium text-foreground">
                                {payload[0].payload.jobs.toLocaleString()}
                            </span>
                        </div>
                    )}
                </div>
            </div>
        );
    }
    return null;
}

function CustomTooltip({ active, payload, label }: any) {
    if (active && payload && payload.length) {
        let dateLabel = '';
        if (typeof label === 'number') {
            // It's a timestamp (Queue History)
            dateLabel = new Date(label).toLocaleString(undefined, {
                month: 'short',
                day: 'numeric',
                hour: '2-digit',
                minute: '2-digit',
            });
        } else {
            // String date from API
            const d = new Date(label);
            // If valid date, format it
            if (!isNaN(d.getTime())) {
                dateLabel = d.toLocaleString(undefined, {
                    month: 'short',
                    day: 'numeric',
                    hour: '2-digit',
                    minute: '2-digit',
                });
            } else {
                dateLabel = label;
            }
        }

        return (
            <div className="bg-popover/95 backdrop-blur-sm border border-border p-3 rounded-lg shadow-lg text-xs">
                <p className="font-medium mb-2 text-popover-foreground">
                    {dateLabel}
                </p>
                <div className="space-y-1">
                    {payload.map((entry: any, index: number) => {
                        let formattedValue = entry.value;
                        const name = entry.name || entry.dataKey;

                        if (typeof entry.value === 'number') {
                            if (
                                name.includes('latency') ||
                                name.includes('Latency')
                            ) {
                                formattedValue = entry.value.toFixed(2) + 's';
                            } else if (
                                name.includes('time') ||
                                name.includes('Time')
                            ) {
                                formattedValue = entry.value.toFixed(2) + 's';
                            } else if (
                                name.includes('rate') ||
                                name.includes('Rate') ||
                                name.includes('Success') ||
                                name.includes('Cache')
                            ) {
                                formattedValue = entry.value.toFixed(1) + '%';
                            } else if (entry.value > 1000) {
                                formattedValue =
                                    (entry.value / 1000).toFixed(1) + 'k';
                            } else if (Number.isInteger(entry.value)) {
                                formattedValue = entry.value;
                            } else {
                                formattedValue = entry.value.toFixed(2);
                            }
                        }

                        return (
                            <div
                                key={index}
                                className="flex items-center gap-2"
                            >
                                <div
                                    className="w-2 h-2 rounded-full"
                                    style={{
                                        backgroundColor:
                                            entry.color ||
                                            entry.fill ||
                                            entry.stroke,
                                    }}
                                />
                                <span className="text-muted-foreground capitalize">
                                    {name.replace(/_/g, ' ')}:
                                </span>
                                <span className="font-mono font-medium text-foreground">
                                    {formattedValue}
                                </span>
                            </div>
                        );
                    })}
                </div>
            </div>
        );
    }
    return null;
}

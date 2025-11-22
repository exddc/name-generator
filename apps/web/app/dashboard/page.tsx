'use client';

import { useSession } from '@/lib/auth-client';
import Link from 'next/link';
import { cn } from '@/lib/utils';
import { useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import { MetricsResponse } from '@/lib/types';
import { Card } from '@/components/ui/card';
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
    CartesianGrid,
    Legend,
} from 'recharts';
import { motion } from 'motion/react';
import {
    ArrowLeft,
    Activity,
    Server,
    Zap,
    AlertCircle,
    CheckCircle,
    Clock,
    Layers,
    Database,
    RefreshCw,
} from 'lucide-react';

import { PageShell, PageHeader } from '@/components/page-layout';

const METRICS_URL = `${process.env.NEXT_PUBLIC_API_URL}/v1/metrics`;

// Brand colors extracted from layout.tsx
const COLORS = {
    pink: '#e59999',
    purple: '#9683dd',
    cyan: '#8fdadb',
    blue: '#3957c0',
    // Additional complementary colors for charts
    indigo: '#6366f1',
    red: '#ef4444',
    success: '#10b981',
};

export default function Dashboard() {
    const { data: session, isPending } = useSession();
    const router = useRouter();
    const [isCheckingAccess, setIsCheckingAccess] = useState(true);
    const [metrics, setMetrics] = useState<MetricsResponse | null>(null);
    const [isLoadingMetrics, setIsLoadingMetrics] = useState(true);

    const formattedChartData = metrics?.chart_data.map((point) => ({
        ...point,
        avg_latency: point.avg_latency / 1000,
        p99_latency: point.p99_latency / 1000,
        avg_generation_time: point.avg_generation_time / 1000,
        avg_check_time: point.avg_check_time / 1000,
        avg_success_rate: point.avg_success_rate * 100,
        cache_hit_rate: point.cache_hit_rate * 100,
    }));

    useEffect(() => {
        if (!isPending && !session?.user) {
            router.push('/login');
            return;
        }

        if (session?.user) {
            const userRole = session.user.role;
            const isAdmin =
                userRole === 'admin' ||
                (typeof userRole === 'string' && userRole.includes('admin')) ||
                (Array.isArray(userRole) && userRole.includes('admin'));

            if (!isAdmin) {
                router.push('/');
                return;
            }

            setIsCheckingAccess(false);
        }
    }, [session, isPending, router]);

    useEffect(() => {
        if (!isCheckingAccess && session?.user) {
            const fetchMetrics = async () => {
                try {
                    const res = await fetch(METRICS_URL);
                    if (res.ok) {
                        const data = await res.json();
                        setMetrics(data);
                    } else {
                        console.error('Failed to fetch metrics');
                    }
                } catch (error) {
                    console.error('Error fetching metrics:', error);
                } finally {
                    setIsLoadingMetrics(false);
                }
            };
            fetchMetrics();
        }
    }, [isCheckingAccess, session]);

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
            <PageHeader
                title="Overview"
                description="System performance and usage metrics."
            />

            <div className="w-full max-w-6xl xl:w-[1152px] space-y-12">
                {isLoadingMetrics ? (
                    <div className="grid grid-cols-1 md:grid-cols-4 gap-6 animate-pulse">
                        {[...Array(4)].map((_, i) => (
                            <div
                                key={i}
                                className="h-32 bg-muted/50 rounded-xl"
                            />
                        ))}
                    </div>
                ) : metrics ? (
                    <div className="space-y-12">
                        {/* Primary Stats */}
                        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-6">
                            <StatsCard
                                icon={<Activity className="w-4 h-4" />}
                                label="Total Suggestions"
                                value={metrics.total_suggestions.toLocaleString()}
                                subValue="Lifetime requests"
                                delay={0.1}
                            />
                            <StatsCard
                                icon={<Layers className="w-4 h-4" />}
                                label="Generated Domains"
                                value={metrics.total_generated_domains.toLocaleString()}
                                subValue="Unique domains"
                                delay={0.2}
                            />
                            <StatsCard
                                icon={<Clock className="w-4 h-4" />}
                                label="Avg Latency"
                                value={`${(
                                    metrics.avg_latency_ms / 1000
                                ).toFixed(2)}s`}
                                subValue={`P99: ${(
                                    metrics.p99_latency_ms / 1000
                                ).toFixed(2)}s`}
                                delay={0.3}
                            />
                            <StatsCard
                                icon={<CheckCircle className="w-4 h-4" />}
                                label="Success Rate"
                                value={`${(
                                    metrics.avg_success_rate * 100
                                ).toFixed(1)}%`}
                                subValue="Completion rate"
                                delay={0.4}
                            />
                        </div>

                        {/* Charts Grid */}
                        <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
                            <ChartCard title="Latency Trends" delay={0.5}>
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
                                                new Date(
                                                    value
                                                ).toLocaleDateString(
                                                    undefined,
                                                    {
                                                        month: 'short',
                                                        day: 'numeric',
                                                    }
                                                )
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
                            </ChartCard>

                            <ChartCard title="Processing Speed" delay={0.6}>
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
                                                new Date(
                                                    value
                                                ).toLocaleDateString(
                                                    undefined,
                                                    {
                                                        month: 'short',
                                                        day: 'numeric',
                                                    }
                                                )
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
                            </ChartCard>

                            <ChartCard title="Yield & Success" delay={0.65}>
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
                                                new Date(
                                                    value
                                                ).toLocaleDateString(
                                                    undefined,
                                                    {
                                                        month: 'short',
                                                        day: 'numeric',
                                                    }
                                                )
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
                            </ChartCard>

                            <ChartCard
                                title="Reliability & Caching"
                                delay={0.7}
                            >
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
                                                new Date(
                                                    value
                                                ).toLocaleDateString(
                                                    undefined,
                                                    {
                                                        month: 'short',
                                                        day: 'numeric',
                                                    }
                                                )
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
                            </ChartCard>

                            <ChartCard title="Resources & Errors" delay={0.8}>
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
                                                new Date(
                                                    value
                                                ).toLocaleDateString(
                                                    undefined,
                                                    {
                                                        month: 'short',
                                                        day: 'numeric',
                                                    }
                                                )
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
                            </ChartCard>
                        </div>

                        {/* Secondary Stats */}
                        <div className="grid grid-cols-1 md:grid-cols-4 gap-6">
                            <StatsCard
                                icon={<Zap className="w-4 h-4" />}
                                label="Resource Usage"
                                value={Math.round(
                                    metrics.avg_tokens_per_request || 0
                                ).toString()}
                                subValue="Tokens / request"
                                delay={0.9}
                                minimal
                            />
                            <StatsCard
                                icon={<Database className="w-4 h-4" />}
                                label="Cache Hit Rate"
                                value={`${(
                                    (metrics.cache_hit_rate || 0) * 100
                                ).toFixed(1)}%`}
                                subValue="Estimated reused"
                                delay={1.0}
                                minimal
                            />
                            <StatsCard
                                icon={<RefreshCw className="w-4 h-4" />}
                                label="Avg Retries"
                                value={(metrics.avg_retry_count || 0).toFixed(
                                    2
                                )}
                                subValue="Per request"
                                delay={1.1}
                                minimal
                            />
                            <StatsCard
                                icon={<AlertCircle className="w-4 h-4" />}
                                label="Total Errors"
                                value={(metrics.total_errors || 0).toString()}
                                subValue="All time"
                                delay={1.2}
                                minimal
                            />
                        </div>
                    </div>
                ) : (
                    <div className="py-20 text-center text-destructive">
                        Failed to load metrics.
                    </div>
                )}
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

function ChartCard({
    title,
    children,
    delay = 0,
}: {
    title: string;
    children: React.ReactNode;
    delay?: number;
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
                <div className="flex-1 min-h-0 w-full">{children}</div>
            </Card>
        </motion.div>
    );
}

function CustomTooltip({ active, payload, label }: any) {
    if (active && payload && payload.length) {
        return (
            <div className="bg-popover/95 backdrop-blur-sm border border-border p-3 rounded-lg shadow-lg text-xs">
                <p className="font-medium mb-2 text-popover-foreground">
                    {new Date(label).toLocaleDateString(undefined, {
                        month: 'long',
                        day: 'numeric',
                    })}
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

export interface Domain {
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
    isNew?: boolean;
}

export enum DomainStatus {
    AVAILABLE = 'available',
    REGISTERED = 'registered',
    UNKNOWN = 'unknown',
}

export enum DomainStatusColor {
    'available' = 'bg-green-300 border-green-500/40 bg-opacity-40',
    'registered' = 'bg-red-300 border-red-500/40 bg-opacity-40',
    'unknown' = 'bg-yellow-300 border-yellow-500/40 bg-opacity-40',
}

// Error handling types
export enum ErrorCode {
    SERVICE_UNAVAILABLE = 'service_unavailable',
    TIMEOUT = 'timeout',
    RATE_LIMITED = 'rate_limited',
    GENERATION_FAILED = 'generation_failed',
    NO_DOMAINS_FOUND = 'no_domains_found',
    INVALID_INPUT = 'invalid_input',
    DOMAIN_NOT_FOUND = 'domain_not_found',
    AUTH_REQUIRED = 'auth_required',
    INTERNAL_ERROR = 'internal_error',
}

export interface ApiError {
    error: boolean;
    code: ErrorCode;
    message: string;
    details?: string | null;
    retry_allowed: boolean;
}

export type StreamMessage = {
    new?: Domain[];
    updates?: Domain[];
    suggestions?: Domain[];
    available_count?: number;
    total?: number;
    // Error fields (when event type is 'error')
    error?: boolean;
    code?: ErrorCode;
    message?: string;
    details?: string | null;
    retry_allowed?: boolean;
};

export type RatingRequestBody = {
    domain: string;
    vote: 1 | -1;
    user_id?: string;
    anon_random_id?: string;
}

export type FavoriteRequestBody = {
    domain: string;
    user_id?: string;
    action: 'fav' | 'unfav';
}

export type TimeSeriesPoint = {
    date: string;
    requests: number;
    avg_latency: number;
    p50_latency: number;
    p99_latency: number;
    avg_success_rate: number;
    avg_generation_time: number;
    avg_check_time: number;
    avg_yield: number;
    avg_tokens: number;
    error_count: number;
    cache_hit_rate: number;
    retry_rate: number;
    avg_queue_depth: number;
}

export type WorkerStat = {
    worker_id: string;
    jobs_processed: number;
    percentage: number;
    last_seen: string;
    is_active: boolean;
    avg_processing_time_ms: number;
}

export type QueueDepthPoint = {
    timestamp: string;
    depth: number;
}

export type MetricsResponse = {
    total_suggestions: number;
    total_domains: number;
    total_generated_domains: number;
    avg_success_rate: number;
    avg_latency_ms: number;
    
    // New detailed metrics
    p99_latency_ms: number;
    avg_generation_time_ms: number;
    avg_check_time_ms: number;
    
    // Domain stats
    domains_per_suggestion: number;
    available_per_suggestion: number;
    unknown_domain_rate: number;
    
    // Resource stats
    avg_tokens_per_request: number;
    total_errors: number;
    
    // Reliability stats
    avg_retry_count: number;
    cache_hit_rate: number;
    
    // Queue & Worker stats
    queue_length: number;
    worker_stats: WorkerStat[];
    queue_history: QueueDepthPoint[];
    
    chart_data: TimeSeriesPoint[];
}

export type MetricsSummaryResponse = {
    total_suggestions: number;
    total_domains: number;
    total_generated_domains: number;
    avg_success_rate: number;
    avg_latency_ms: number;
    p99_latency_ms: number;
    avg_generation_time_ms: number;
    avg_check_time_ms: number;
    domains_per_suggestion: number;
    available_per_suggestion: number;
    unknown_domain_rate: number;
    avg_tokens_per_request: number;
    total_errors: number;
    avg_retry_count: number;
    cache_hit_rate: number;
}

export type MetricsHistoryResponse = {
    chart_data: TimeSeriesPoint[];
}

export type MetricsQueueResponse = {
    queue_length: number;
    queue_history: QueueDepthPoint[];
    avg_queue_wait_time_ms: number;
}

export type MetricsWorkerResponse = {
    worker_stats: WorkerStat[];
    active_workers: number;
    total_workers: number;
    avg_processing_time_ms: number;
}

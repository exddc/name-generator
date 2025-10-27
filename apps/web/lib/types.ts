export interface Domain {
    domain: string;
    tld: string;
    status: DomainStatus;
    rating?: number;
    created_at: string;
    updated_at: string;
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

export type StreamMessage = {
    new?: Domain[];
    updates?: Domain[];
    suggestions?: Domain[];
    available_count?: number;
    total?: number;
};
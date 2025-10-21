export interface Domain {
    domain: string;
    status: DomainStatus;
    last_checked: string;
    rating: number;
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

// TODO: Remove this once the API is updated
export type DomainFeedback = {
    [domain: string]: number | undefined;
  };
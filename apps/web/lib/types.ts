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

// TODO: Remove this once the API is updated
export interface DomainData {
    domain: string;
    status: string;
}

export type DomainFeedback = {
    [domain: string]: number | undefined;
  };
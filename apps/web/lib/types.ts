export interface Domain {
    domain: string;
    status: string;
    last_checked: string;
    rating: number;
}

// TODO: Remove this once the API is updated
export interface DomainData {
    domain: string;
    status: string;
}

export type DomainFeedback = {
    [domain: string]: number | undefined;
  };
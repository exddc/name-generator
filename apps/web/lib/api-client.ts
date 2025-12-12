'use client';

type CachedToken = {
    token: string;
    expiresAt: number;
};

let cachedToken: CachedToken | null = null;
let inflightRequest: Promise<CachedToken> | null = null;

const TOKEN_ENDPOINT = '/api/token';
const SAFETY_WINDOW_MS = 15_000;

async function requestNewToken(): Promise<CachedToken> {
    const response = await fetch(TOKEN_ENDPOINT, {
        method: 'GET',
        credentials: 'include',
    });

    if (response.status === 401) {
        throw new Error('AUTH_REQUIRED');
    }

    if (!response.ok) {
        const errorBody = await response.text();
        throw new Error(
            `Unable to issue API token (${response.status} ${response.statusText}): ${errorBody}`
        );
    }

    const data = await response.json();
    const ttlSeconds = Number(data?.ttl_seconds) || 0;
    const expiresAt =
        (data?.expires_at ? new Date(data.expires_at).getTime() : Date.now() + ttlSeconds * 1000) ||
        Date.now();

    return { token: data.token, expiresAt };
}

export function invalidateApiToken() {
    cachedToken = null;
}

export async function getApiToken(forceRefresh = false): Promise<string> {
    if (!forceRefresh && cachedToken && cachedToken.expiresAt - Date.now() > SAFETY_WINDOW_MS) {
        return cachedToken.token;
    }

    if (!inflightRequest) {
        inflightRequest = requestNewToken()
            .then((tokenData) => {
                cachedToken = tokenData;
                return tokenData;
            })
            .finally(() => {
                inflightRequest = null;
            });
    }

    const tokenData = await inflightRequest;
    return tokenData.token;
}

export async function apiFetch(
    input: RequestInfo | URL,
    init: RequestInit = {},
    retry = true
): Promise<Response> {
    try {
        const token = await getApiToken();
        const headers = new Headers(init.headers);
        headers.set('Authorization', `Bearer ${token}`);

        const response = await fetch(input, {
            ...init,
            headers,
        });

        if (response.status === 401 && retry) {
            invalidateApiToken();
            return apiFetch(input, init, false);
        }

        return response;
    } catch (error) {
        if ((error as Error)?.message === 'AUTH_REQUIRED') {
            throw new Error('AUTH_REQUIRED');
        }
        throw error;
    }
}

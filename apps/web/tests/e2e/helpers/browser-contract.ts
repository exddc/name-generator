import { expect, type Page, type Route } from '@playwright/test';

export const GENERATED_DOMAIN = {
    domain: 'baselineproof.com',
    tld: 'com',
    status: 'available',
    rating: null,
    created_at: '2026-01-01T00:00:00Z',
    updated_at: '2026-01-01T00:00:00Z',
} as const;

export const PROMPT_PLACEHOLDER =
    'Describe your app, service, or company idea...';

export type CapturedWrite = {
    method: string;
    url: string;
    body: Record<string, unknown>;
};

export async function mockAnonymousSession(page: Page) {
    await page.route('**/api/auth/get-session**', (route) =>
        route.fulfill({
            status: 200,
            contentType: 'application/json',
            body: 'null',
        })
    );
}

export async function mockAuthenticatedSession(
    page: Page,
    userId = 'browser-user-123'
) {
    await page.route('**/api/auth/get-session**', (route) =>
        route.fulfill({
            status: 200,
            contentType: 'application/json',
            body: JSON.stringify({
                user: {
                    id: userId,
                    email: 'browser@example.test',
                    name: 'Browser Test',
                },
                session: { id: 'browser-session', userId },
            }),
        })
    );
}

export async function mockToken(page: Page, token = 'browser-test-token') {
    await page.route('**/api/token', (route) =>
        route.fulfill({
            status: 200,
            contentType: 'application/json',
            body: JSON.stringify({
                token,
                ttl_seconds: 300,
                expires_at: new Date(Date.now() + 300_000).toISOString(),
            }),
        })
    );
}

export async function mockGeneration(
    page: Page,
    domain: typeof GENERATED_DOMAIN = GENERATED_DOMAIN
) {
    await page.route('**/v1/domain/stream', (route) =>
        route.fulfill({
            status: 200,
            contentType: 'text/event-stream',
            body: [
                'event: start',
                'data: {"requested_count":1,"max_retries":1}',
                '',
                'event: heartbeat',
                'data: {"timestamp":"2026-01-01T00:00:00Z"}',
                '',
                'event: suggestions',
                `data: ${JSON.stringify({ new: [domain], updates: [], total: 1 })}`,
                '',
                'event: complete',
                `data: ${JSON.stringify({ suggestions: [domain], total: 1 })}`,
                '',
                '',
            ].join('\n'),
        })
    );
}

function emptyListBody(key: 'ratings' | 'favorites') {
    return JSON.stringify({
        [key]: [],
        total: 0,
        page: 1,
        page_size: 100,
    });
}

export async function mockRatingReads(page: Page) {
    await page.route('**/v1/domain/rating**', async (route: Route) => {
        if (route.request().method() !== 'GET') {
            await route.fallback();
            return;
        }
        await route.fulfill({
            status: 200,
            contentType: 'application/json',
            body: emptyListBody('ratings'),
        });
    });
}

export async function mockFavoriteReads(page: Page) {
    await page.route('**/v1/user/favorite**', async (route: Route) => {
        if (route.request().method() !== 'GET') {
            await route.fallback();
            return;
        }
        await route.fulfill({
            status: 200,
            contentType: 'application/json',
            body: emptyListBody('favorites'),
        });
    });
}

/** Capture POST writes to rating + favorite; fulfill success responses. */
export async function mockWriteCaptures(
    page: Page,
    writes: CapturedWrite[],
    domain = GENERATED_DOMAIN.domain
) {
    await page.route('**/v1/domain/rating**', async (route) => {
        const request = route.request();
        if (request.method() === 'POST') {
            writes.push({
                method: request.method(),
                url: request.url(),
                body: request.postDataJSON() as Record<string, unknown>,
            });
            await route.fulfill({
                status: 200,
                contentType: 'application/json',
                body: JSON.stringify({ id: 1, domain, vote: 1 }),
            });
            return;
        }
        await route.fulfill({
            status: 200,
            contentType: 'application/json',
            body: emptyListBody('ratings'),
        });
    });

    await page.route('**/v1/user/favorite**', async (route) => {
        const request = route.request();
        if (request.method() === 'POST') {
            writes.push({
                method: request.method(),
                url: request.url(),
                body: request.postDataJSON() as Record<string, unknown>,
            });
            await route.fulfill({
                status: 200,
                contentType: 'application/json',
                body: JSON.stringify({
                    success: true,
                    action: 'fav',
                    domain,
                }),
            });
            return;
        }
        await route.fulfill({
            status: 200,
            contentType: 'application/json',
            body: emptyListBody('favorites'),
        });
    });
}

export async function submitGeneration(
    page: Page,
    domain = GENERATED_DOMAIN.domain
) {
    const input = page.getByPlaceholder(PROMPT_PLACEHOLDER);
    await input.fill('A testable naming service');
    await input.press('Enter');
    await expect(page.getByRole('link', { name: domain })).toBeVisible();
}

export function pathOf(url: string): string {
    return new URL(url).pathname;
}

import { expect, Page, test } from '@playwright/test';

const generatedDomain = {
    domain: 'baselineproof.com',
    tld: 'com',
    status: 'available',
    rating: null,
    created_at: '2026-01-01T00:00:00Z',
    updated_at: '2026-01-01T00:00:00Z',
};

async function mockToken(page: Page) {
    await page.route('**/api/token', (route) =>
        route.fulfill({
            status: 200,
            contentType: 'application/json',
            body: JSON.stringify({
                token: 'browser-test-token',
                ttl_seconds: 300,
                expires_at: new Date(Date.now() + 300_000).toISOString(),
            }),
        })
    );
}

async function mockGeneration(page: Page) {
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
                `data: ${JSON.stringify({ new: [generatedDomain], updates: [], total: 1 })}`,
                '',
                'event: complete',
                `data: ${JSON.stringify({ suggestions: [generatedDomain], total: 1 })}`,
                '',
                '',
            ].join('\n'),
        })
    );
}

async function submitGeneration(page: Page) {
    const input = page.getByPlaceholder(
        'Describe your app, service, or company idea...'
    );
    await input.fill('A testable naming service');
    await input.press('Enter');
    await expect(page.getByRole('link', { name: generatedDomain.domain })).toBeVisible();
}

test('anonymous visitor can generate domains', async ({ page }) => {
    await page.route('**/api/auth/get-session**', (route) =>
        route.fulfill({ status: 200, contentType: 'application/json', body: 'null' })
    );
    await mockToken(page);
    await mockGeneration(page);
    await page.route('**/v1/domain/rating**', (route) =>
        route.fulfill({
            status: 200,
            contentType: 'application/json',
            body: JSON.stringify({ ratings: [], total: 0, page: 1, page_size: 100 }),
        })
    );

    await page.goto('/');
    await submitGeneration(page);
});

test('authenticated visitor can save and rate a generated domain', async ({ page }) => {
    const userId = 'browser-user-123';
    const writes: Array<{ url: string; body: Record<string, unknown> }> = [];

    await page.route('**/api/auth/get-session**', (route) =>
        route.fulfill({
            status: 200,
            contentType: 'application/json',
            body: JSON.stringify({
                user: { id: userId, email: 'browser@example.test', name: 'Browser Test' },
                session: { id: 'browser-session', userId },
            }),
        })
    );
    await mockToken(page);
    await mockGeneration(page);
    await page.route('**/v1/domain/rating**', async (route) => {
        if (route.request().method() === 'POST') {
            writes.push({
                url: route.request().url(),
                body: route.request().postDataJSON(),
            });
            await route.fulfill({
                status: 200,
                contentType: 'application/json',
                body: JSON.stringify({ id: 1, domain: generatedDomain.domain, vote: 1 }),
            });
            return;
        }
        await route.fulfill({
            status: 200,
            contentType: 'application/json',
            body: JSON.stringify({ ratings: [], total: 0, page: 1, page_size: 100 }),
        });
    });
    await page.route('**/v1/user/favorite**', async (route) => {
        if (route.request().method() === 'POST') {
            writes.push({
                url: route.request().url(),
                body: route.request().postDataJSON(),
            });
            await route.fulfill({
                status: 200,
                contentType: 'application/json',
                body: JSON.stringify({ success: true, action: 'fav', domain: generatedDomain.domain }),
            });
            return;
        }
        await route.fulfill({
            status: 200,
            contentType: 'application/json',
            body: JSON.stringify({ favorites: [], total: 0, page: 1, page_size: 100 }),
        });
    });

    await page.goto('/');
    await submitGeneration(page);
    await page.getByRole('button', { name: `Upvote ${generatedDomain.domain}` }).click();
    await page.getByRole('button', { name: `Save ${generatedDomain.domain}` }).click();

    await expect.poll(() => writes.length).toBe(2);
    expect(writes.map((write) => write.body)).toEqual(
        expect.arrayContaining([
            { domain: generatedDomain.domain, vote: 1 },
            { domain: generatedDomain.domain, user_id: userId, action: 'fav' },
        ])
    );
});

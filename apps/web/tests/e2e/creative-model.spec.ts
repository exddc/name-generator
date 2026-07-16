import { expect, test } from '@playwright/test';
import { SignJWT } from 'jose';

const API_STREAM_PATH = '/v1/domain/stream';
const MODEL_120B = 'openai/gpt-oss-120b';

test('Get creative uses GPT-OSS 120B', async ({ page }) => {
    test.skip(
        process.env.RUN_CREATIVE_E2E !== '1' || !process.env.API_JWT_SECRET,
        'set RUN_CREATIVE_E2E=1 and API_JWT_SECRET to exercise the live local stack'
    );

    const now = Math.floor(Date.now() / 1000);
    const token = await new SignJWT({
        email: 'tw-266-playwright@example.test',
        session_id: 'tw-266-playwright',
        scopes: [],
    })
        .setProtectedHeader({ alg: 'HS256' })
        .setSubject('tw-266-playwright')
        .setIssuedAt(now)
        .setExpirationTime(now + 300)
        .setIssuer(process.env.API_JWT_ISSUER || 'domain-generator-web')
        .setAudience(process.env.API_JWT_AUDIENCE || 'domain-generator-api')
        .sign(new TextEncoder().encode(process.env.API_JWT_SECRET));

    await page.route('**/api/token', async (route) => {
        await route.fulfill({
            status: 200,
            contentType: 'application/json',
            body: JSON.stringify({
                token,
                ttl_seconds: 300,
                expires_at: new Date((now + 300) * 1000).toISOString(),
            }),
        });
    });

    await page.route(`**${API_STREAM_PATH}`, async (route) => {
        const body = route.request().postDataJSON() as { creative?: boolean };
        if (body.creative) {
            await route.continue({
                postData: JSON.stringify({ ...body, count: 1 }),
                headers: {
                    ...route.request().headers(),
                    'content-type': 'application/json',
                },
            });
            return;
        }

        const timestamp = new Date().toISOString();
        const suggestion = {
            domain: 'initialproof.com',
            tld: 'com',
            status: 'available',
            rating: null,
            created_at: timestamp,
            updated_at: timestamp,
        };
        await route.fulfill({
            status: 200,
            contentType: 'text/event-stream',
            body: [
                'event: start',
                'data: {"requested_count":1,"max_retries":1}',
                '',
                'event: complete',
                `data: ${JSON.stringify({ suggestions: [suggestion], available_count: 1, total: 1 })}`,
                '',
                '',
            ].join('\n'),
        });
    });

    await page.goto('/');
    await page
        .getByPlaceholder('Describe your app, service, or company idea...')
        .fill('A collaborative writing studio');
    await page
        .getByPlaceholder('Describe your app, service, or company idea...')
        .press('Enter');

    const creativeButton = page.getByRole('button', { name: 'Get creative' });
    await expect(creativeButton).toBeVisible();

    const creativeResponsePromise = page.waitForResponse((response) => {
        if (!response.url().endsWith(API_STREAM_PATH)) return false;
        const body = response.request().postDataJSON() as { creative?: boolean };
        return body.creative === true;
    });
    await creativeButton.click();
    const creativeResponse = await creativeResponsePromise;
    expect(creativeResponse.ok()).toBeTruthy();
    const stream = await creativeResponse.text();
    expect(stream).toContain(`"requested_model": "${MODEL_120B}"`);
    expect(stream).toContain(`"model": "${MODEL_120B}"`);
    expect(stream).toContain('"fallback_used": false');
});

import { expect, test } from '@playwright/test';
import {
    GENERATED_DOMAIN,
    mockAnonymousSession,
    mockAuthenticatedSession,
    mockGeneration,
    mockToken,
    mockWriteCaptures,
    pathOf,
    submitGeneration,
    type CapturedWrite,
} from './helpers/browser-contract';

test('anonymous visitor can generate domains', async ({ page }) => {
    const writes: CapturedWrite[] = [];

    await mockAnonymousSession(page);
    await mockToken(page);
    await mockGeneration(page);
    await mockWriteCaptures(page, writes);

    await page.goto('/');
    await submitGeneration(page);

    const save = page.getByRole('button', {
        name: `Save ${GENERATED_DOMAIN.domain}`,
    });
    await expect(save).toBeVisible();
    await expect(save).toHaveClass(/opacity-50/);

    await save.click();
    // Guests see a sign-in toast and must not POST favorites.
    await expect
        .poll(() => writes.filter((w) => pathOf(w.url).includes('/favorite')))
        .toEqual([]);
});

test('authenticated visitor can save and rate a generated domain', async ({
    page,
}) => {
    const userId = 'browser-user-123';
    const writes: CapturedWrite[] = [];

    await mockAuthenticatedSession(page, userId);
    await mockToken(page);
    await mockGeneration(page);
    await mockWriteCaptures(page, writes);

    await page.goto('/');
    await submitGeneration(page);

    await page
        .getByRole('button', { name: `Upvote ${GENERATED_DOMAIN.domain}` })
        .click();
    await page
        .getByRole('button', { name: `Save ${GENERATED_DOMAIN.domain}` })
        .click();

    await expect.poll(() => writes.length).toBe(2);

    const rating = writes.find((w) => pathOf(w.url).endsWith('/v1/domain/rating'));
    const favorite = writes.find((w) =>
        pathOf(w.url).endsWith('/v1/user/favorite')
    );

    expect(rating).toMatchObject({
        method: 'POST',
        body: { domain: GENERATED_DOMAIN.domain, vote: 1 },
    });
    expect(favorite).toMatchObject({
        method: 'POST',
        body: {
            domain: GENERATED_DOMAIN.domain,
            user_id: userId,
            action: 'fav',
        },
    });
});

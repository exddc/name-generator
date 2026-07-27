import { defineConfig } from '@playwright/test';

const port = Number(process.env.PLAYWRIGHT_PORT || 3100);
const isCI = !!process.env.CI;

export default defineConfig({
    testDir: './tests/e2e',
    timeout: 120_000,
    fullyParallel: false,
    forbidOnly: isCI,
    retries: isCI ? 1 : 0,
    reporter: isCI
        ? [['list'], ['html', { open: 'never', outputFolder: 'playwright-report' }]]
        : 'list',
    use: {
        baseURL: `http://127.0.0.1:${port}`,
        trace: 'retain-on-failure',
        screenshot: 'only-on-failure',
    },
    webServer: {
        command: `bun run dev -- --hostname 127.0.0.1 --port ${port}`,
        url: `http://127.0.0.1:${port}`,
        reuseExistingServer: !isCI,
        timeout: 120_000,
    },
});

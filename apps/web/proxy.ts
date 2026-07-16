import { NextResponse } from 'next/server';
import type { NextRequest } from 'next/server';

// This app defines no Server Actions. Bots and security scanners routinely POST a
// `Next-Action` header to probe for Next.js server-action CVEs, and Next logs a noisy
// "Failed to find Server Action" error for every one of them. Short-circuit those
// requests here so they never reach — or spam the logs of — the action handler.
// Legitimate requests (page loads, /api/auth, the token route) never carry this
// header, so they fall through untouched.
export function proxy(request: NextRequest) {
    if (request.method === 'POST' && request.headers.has('next-action')) {
        return new NextResponse('Server action not found.', {
            status: 404,
            headers: { 'x-nextjs-action-not-found': '1' },
        });
    }

    return NextResponse.next();
}

export const config = {
    matcher: ['/((?!_next/static|_next/image|favicon.ico).*)'],
};

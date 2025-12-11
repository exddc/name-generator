import { auth } from '@/lib/auth';
import { cookies } from 'next/headers';
import { NextRequest, NextResponse } from 'next/server';
import { SignJWT } from 'jose';
import { randomUUID } from 'crypto';

type SessionResult = {
    user: {
        id: string;
        email: string;
        name?: string | null;
        role?: string | null;
    };
    session: {
        id: string;
        scopes?: string[];
    };
} | null;

const textEncoder = new TextEncoder();

const DEFAULT_TTL_SECONDS = 300;
const DEFAULT_ISSUER = 'domain-generator-web';
const DEFAULT_AUDIENCE = 'domain-generator-api';
const DEFAULT_ALGORITHM = 'HS256';
const DEFAULT_ANON_COOKIE = 'dg_anon_id';
const DEFAULT_ANON_COOKIE_MAX_AGE = 60 * 60 * 24 * 30; // 30 days

async function issueToken(request: NextRequest) {
    const secret = process.env.API_JWT_SECRET;
    if (!secret) {
        return NextResponse.json(
            { error: 'Token issuing is disabled. API_JWT_SECRET is not configured.' },
            { status: 503 }
        );
    }

    const cookieStore = cookies();

    let sessionResult: SessionResult = null;
    try {
        sessionResult = (await auth.api.getSession({
            headers: request.headers,
        })) as SessionResult;
    } catch (error) {
        console.error('[token] Failed to load session', error);
        sessionResult = null;
    }

    const ttlInput = Number(process.env.API_JWT_TTL_SECONDS ?? DEFAULT_TTL_SECONDS);
    const ttlSeconds = Number.isFinite(ttlInput) && ttlInput > 0 ? ttlInput : DEFAULT_TTL_SECONDS;
    const issuedAt = Math.floor(Date.now() / 1000);
    const expiresAt = issuedAt + ttlSeconds;

    const issuer = process.env.API_JWT_ISSUER || DEFAULT_ISSUER;
    const audience = process.env.API_JWT_AUDIENCE || DEFAULT_AUDIENCE;
    const algorithm = process.env.API_JWT_ALGORITHM || DEFAULT_ALGORITHM;

    const anonCookieName = process.env.API_ANON_COOKIE_NAME || DEFAULT_ANON_COOKIE;
    const anonCookieMaxAge =
        Number(process.env.API_ANON_COOKIE_MAX_AGE ?? DEFAULT_ANON_COOKIE_MAX_AGE) ||
        DEFAULT_ANON_COOKIE_MAX_AGE;

    let subject: string;
    let email: string | undefined;
    let name: string | undefined;
    let sessionId: string;
    let scopes: string[] = [];
    let shouldSetAnonCookie = false;
    let anonId: string | null = null;

    if (sessionResult?.user && sessionResult.session) {
        subject = sessionResult.user.id;
        email = sessionResult.user.email;
        name = sessionResult.user.name ?? undefined;
        sessionId = sessionResult.session.id;

        const initialScopes = Array.isArray(sessionResult.session.scopes)
            ? sessionResult.session.scopes
            : [];
        scopes =
            sessionResult.user.role === 'admin'
                ? Array.from(new Set([...initialScopes, 'metrics:read']))
                : initialScopes;
    } else {
        anonId = cookieStore.get(anonCookieName)?.value ?? null;
        if (!anonId) {
            anonId = randomUUID();
            shouldSetAnonCookie = true;
        }
        subject = `anon:${anonId}`;
        sessionId = subject;
        email = undefined;
        name = undefined;
        scopes = [];
    }

    const payload = {
        sub: subject,
        email,
        name,
        session_id: sessionId,
        scopes,
    };

    let token: string;
    try {
        token = await new SignJWT(payload)
            .setProtectedHeader({ alg: algorithm, typ: 'JWT' })
            .setIssuedAt(issuedAt)
            .setExpirationTime(expiresAt)
            .setIssuer(issuer)
            .setAudience(audience)
            .sign(textEncoder.encode(secret));
    } catch (error) {
        console.error('[token] Failed to sign JWT', error);
        return NextResponse.json(
            { error: 'Unable to generate token. Please try again.' },
            { status: 500 }
        );
    }

    const response = NextResponse.json({
        token,
        expires_at: new Date(expiresAt * 1000).toISOString(),
        ttl_seconds: ttlSeconds,
    });

    if (shouldSetAnonCookie && anonId) {
        response.cookies.set(anonCookieName, anonId, {
            httpOnly: true,
            sameSite: 'lax',
            secure: process.env.NODE_ENV === 'production',
            maxAge: anonCookieMaxAge,
            path: '/',
        });
    }

    return response;
}

export async function GET(request: NextRequest) {
    return issueToken(request);
}

export async function POST(request: NextRequest) {
    return issueToken(request);
}

import { auth } from '@/lib/auth';
import { NextRequest, NextResponse } from 'next/server';
import { SignJWT } from 'jose';

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

async function issueToken(request: NextRequest) {
    const secret = process.env.API_JWT_SECRET;
    if (!secret) {
        return NextResponse.json(
            { error: 'Token issuing is disabled. API_JWT_SECRET is not configured.' },
            { status: 503 }
        );
    }

    let sessionResult: SessionResult = null;
    try {
        sessionResult = (await auth.api.getSession({
            headers: request.headers,
        })) as SessionResult;
    } catch (error) {
        console.error('[token] Failed to load session', error);
        return NextResponse.json(
            { error: 'Unable to load session. Please refresh and try again.' },
            { status: 500 }
        );
    }

    if (!sessionResult?.user || !sessionResult?.session) {
        return NextResponse.json({ error: 'Unauthorized' }, { status: 401 });
    }

    const ttlInput = Number(process.env.API_JWT_TTL_SECONDS ?? DEFAULT_TTL_SECONDS);
    const ttlSeconds = Number.isFinite(ttlInput) && ttlInput > 0 ? ttlInput : DEFAULT_TTL_SECONDS;
    const issuedAt = Math.floor(Date.now() / 1000);
    const expiresAt = issuedAt + ttlSeconds;

    const issuer = process.env.API_JWT_ISSUER || DEFAULT_ISSUER;
    const audience = process.env.API_JWT_AUDIENCE || DEFAULT_AUDIENCE;
    const algorithm = process.env.API_JWT_ALGORITHM || DEFAULT_ALGORITHM;

    const initialScopes = Array.isArray(sessionResult.session.scopes)
        ? sessionResult.session.scopes
        : [];
    const scopes =
        sessionResult.user.role === 'admin'
            ? Array.from(new Set([...initialScopes, 'metrics:read']))
            : initialScopes;

    const payload = {
        sub: sessionResult.user.id,
        email: sessionResult.user.email,
        name: sessionResult.user.name,
        session_id: sessionResult.session.id,
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

    return NextResponse.json({
        token,
        expires_at: new Date(expiresAt * 1000).toISOString(),
        ttl_seconds: ttlSeconds,
    });
}

export async function GET(request: NextRequest) {
    return issueToken(request);
}

export async function POST(request: NextRequest) {
    return issueToken(request);
}

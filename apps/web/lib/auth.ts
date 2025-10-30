import { betterAuth } from "better-auth";
import { magicLink } from "better-auth/plugins";
import { admin } from "better-auth/plugins";
import { Pool } from "pg";

// Postgres connection pool
const pool = new Pool({
    host: process.env.POSTGRES_HOST || process.env.DB_HOST || "127.0.0.1",
    port: parseInt(process.env.POSTGRES_PORT || process.env.DB_PORT || "5432"),
    user: process.env.POSTGRES_USER || process.env.DB_USER || "postgres",
    password: process.env.POSTGRES_PASSWORD || process.env.DB_PASSWORD || "password",
    database: process.env.POSTGRES_DB || process.env.DB_NAME || "domain_generator",
});

export const auth = betterAuth({
    database: pool,
    baseURL: process.env.BETTER_AUTH_URL || process.env.NEXT_PUBLIC_BETTER_AUTH_URL || "http://localhost:3000",
    secret: process.env.BETTER_AUTH_SECRET || process.env.AUTH_SECRET || "better-auth-secret-123456789",
    trustedOrigins: [
        process.env.BETTER_AUTH_URL || "http://localhost:3000",
        ...(process.env.NODE_ENV === "production" ? [] : ["http://localhost:3000"]),
    ],
    plugins: [
        magicLink({
            async sendMagicLink({ email, token, url }) {
                try {
                    // Log the magic link for development
                    // NOTE: These logs appear in your SERVER terminal/console, not the browser console!
                    console.log('\n========================================');
                    console.log('🔗 MAGIC LINK REQUEST');
                    console.log('========================================');
                    console.log(`Email: ${email}`);
                    console.log(`Magic Link URL: ${url}`);
                    console.log(`Token: ${token}`);
                    console.log(`\n📧 Copy this URL and open it in your browser to sign in:`);
                    console.log(`   ${url}`);
                    console.log('========================================\n');
                    
                    // TODO: Implement email sending service for production
                    // Example with Resend:
                    // import { Resend } from 'resend';
                    // const resend = new Resend(process.env.RESEND_API_KEY);
                    // await resend.emails.send({
                    //     from: 'noreply@yourdomain.com',
                    //     to: email,
                    //     subject: 'Sign in to Domain Generator',
                    //     html: `<a href="${url}">Click here to sign in</a>`,
                    // });
                } catch (error) {
                    console.error('Error in sendMagicLink:', error);
                    throw error;
                }
            },
        }),
        admin(),
    ],
});


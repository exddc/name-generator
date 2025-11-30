import { betterAuth } from "better-auth";
import { magicLink } from "better-auth/plugins";
import { emailOTP } from "better-auth/plugins";
import { admin } from "better-auth/plugins";
import { Pool } from "pg";
import { Resend } from "resend";

// Postgres connection pool
const pool = new Pool({
    host: process.env.POSTGRES_HOST || process.env.DB_HOST || "127.0.0.1",
    port: parseInt(process.env.POSTGRES_PORT || process.env.DB_PORT || "5432"),
    user: process.env.POSTGRES_USER || process.env.DB_USER || "postgres",
    password: process.env.POSTGRES_PASSWORD || process.env.DB_PASSWORD || "password",
    database: process.env.POSTGRES_DB || process.env.DB_NAME || "domain_generator",
});

const resendApiKey = process.env.RESEND_API_KEY;
const resendFromEmail =
    process.env.RESEND_FROM_EMAIL || "magic@updates.timoweiss.me";
const resendClient = resendApiKey ? new Resend(resendApiKey) : null;

const buildLoginEmailHtml = (url: string, code: string) =>
    `
<p>Hi there,</p>
<p>Click the link below to sign in to Domain Generator:</p>
<p><a href="${url}">Login to Domain Generator</a></p>
<p>Alternatively, you can use the code below to sign in:</p>
<p style="font-size: 24px; font-weight: bold; letter-spacing: 4px; text-align: center; padding: 20px; background-color: #f3f4f6; border-radius: 8px; margin: 20px 0;">${code}</p>
<p>This code and link will expire shortly. If you didn't request it, feel free to ignore this email.</p>
`.trim();

const buildLoginEmailText = (url: string, code: string) =>
    `Use the link below to sign in to Domain Generator:\n\n${url}\n\nAlternatively, you can use the code below to sign in:\n\n${code}\n\nThis code and link will expire shortly.`;



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
                    if (!resendClient) {
                        console.warn(
                            "RESEND_API_KEY is not set. Falling back to console logging the magic link."
                        );
                        console.log("\n========================================");
                        console.log("🔗 MAGIC LINK REQUEST");
                        console.log("========================================");
                        console.log(`Email: ${email}`);
                        console.log(`Magic Link URL: ${url}`);
                        console.log(`Token: ${token}`);
                        console.log(
                            `\n📧 Copy this URL and open it in your browser to sign in:`
                        );
                        console.log(`   ${url}`);
                        console.log("========================================\n");
                        return;
                    }

                    await resendClient.emails.send({
                        from: `Domain Generator <${resendFromEmail}>`,
                        to: email,
                        subject: "Sign in to Domain Generator",
                        html: `<p>Click to sign in: <a href="${url}">${url}</a></p>`,
                        text: `Click to sign in: ${url}`,
                    });
                } catch (error) {
                    console.error("Error in sendMagicLink:", error);
                    throw error;
                }
            },
        }),
        emailOTP({
            async sendVerificationOTP({ email, otp, type }) {
                console.log(`sendVerificationOTP called for ${email}`);
                try {
                    if (!resendClient || process.env.NODE_ENV === "development") {
                        if (!resendClient) {
                            console.warn(
                                "RESEND_API_KEY is not set. Falling back to console logging the OTP code."
                            );
                        }
                        console.log("\n========================================");
                        console.log("🔢 OTP CODE REQUEST");
                        console.log("========================================");
                        console.log(`Email: ${email}`);
                        console.log(`OTP Code: ${otp}`);
                        console.log(
                            `\n📧 Your 6-digit code is: ${otp}`
                        );
                        console.log("========================================\n");
                        if (!resendClient) return;
                    }

                    const url = `${process.env.NEXT_PUBLIC_APP_URL || process.env.BETTER_AUTH_URL || "http://localhost:3000"}/login?email=${encodeURIComponent(email)}&otp=${otp}`;

                    await resendClient.emails.send({
                        from: `Domain Generator <${resendFromEmail}>`,
                        to: email,
                        subject: "Sign in to Domain Generator",
                        html: buildLoginEmailHtml(url, otp),
                        text: buildLoginEmailText(url, otp),
                    });
                } catch (error) {
                    console.error("Error in sendVerificationOTP:", error);
                    throw error;
                }
            },
        }),
        admin(),
    ],
});

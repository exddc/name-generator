FROM oven/bun:1.3.0 AS dependencies

WORKDIR /app
COPY package.json bun.lock ./
RUN bun install --frozen-lockfile

FROM oven/bun:1.3.0 AS builder

WORKDIR /app
ARG NEXT_PUBLIC_API_URL=http://localhost:8000
ARG NEXT_PUBLIC_BETTER_AUTH_URL=http://localhost:3000
ENV NEXT_TELEMETRY_DISABLED=1 \
    NEXT_PUBLIC_API_URL=${NEXT_PUBLIC_API_URL} \
    NEXT_PUBLIC_BETTER_AUTH_URL=${NEXT_PUBLIC_BETTER_AUTH_URL}

COPY --from=dependencies /app/node_modules ./node_modules
COPY --from=dependencies /app/package.json ./package.json
COPY --from=dependencies /app/bun.lock ./bun.lock
COPY . .
RUN BETTER_AUTH_SECRET=build-only-placeholder-secret-32-bytes \
    API_JWT_SECRET=build-only-placeholder-secret-32-bytes \
    bun run build

FROM oven/bun:1.3.0 AS runtime

WORKDIR /app
ARG PORT=3000
ENV NODE_ENV=production \
    NEXT_TELEMETRY_DISABLED=1 \
    HOSTNAME=0.0.0.0 \
    PORT=${PORT}

RUN groupadd --system --gid 1001 bunjs \
    && useradd --system --uid 1001 --gid bunjs nextjs

COPY --from=builder --chown=nextjs:bunjs /app/public ./public
COPY --from=builder --chown=nextjs:bunjs /app/.next ./.next
COPY --from=builder --chown=nextjs:bunjs /app/node_modules ./node_modules
COPY --from=builder --chown=nextjs:bunjs /app/package.json ./package.json
COPY --from=builder --chown=nextjs:bunjs /app/next.config.ts ./next.config.ts

USER nextjs
EXPOSE ${PORT}
CMD ["bun", "run", "start"]

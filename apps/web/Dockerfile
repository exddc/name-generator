FROM oven/bun:1.3

RUN apt-get update \
    && apt-get install -y --no-install-recommends curl ca-certificates gnupg \
    && curl -fsSL https://deb.nodesource.com/setup_20.x | bash - \
    && apt-get install -y --no-install-recommends nodejs \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

ARG NEXT_PUBLIC_API_URL=http://localhost:8000
ARG NEXT_PUBLIC_SUGGEST_ENDPOINT
ARG BETTER_AUTH_URL=http://localhost:3000
ARG NEXT_PUBLIC_BETTER_AUTH_URL=http://localhost:3000
ARG BETTER_AUTH_SECRET
ARG PORT=3000

ENV NODE_ENV=production \
    NEXT_TELEMETRY_DISABLED=1 \
    NEXT_PUBLIC_API_URL=${NEXT_PUBLIC_API_URL} \
    NEXT_PUBLIC_SUGGEST_ENDPOINT=${NEXT_PUBLIC_SUGGEST_ENDPOINT} \
    BETTER_AUTH_URL=${BETTER_AUTH_URL} \
    NEXT_PUBLIC_BETTER_AUTH_URL=${NEXT_PUBLIC_BETTER_AUTH_URL} \
    BETTER_AUTH_SECRET=${BETTER_AUTH_SECRET} \
    PORT=${PORT}

COPY package.json package-lock.json ./

RUN bun install --no-save

COPY . .

RUN bun run build

EXPOSE ${PORT}

CMD ["bun", "run", "start"]
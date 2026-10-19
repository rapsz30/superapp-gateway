FROM node:22-bookworm-slim

ENV NEXT_TELEMETRY_DISABLED=1
WORKDIR /app

# poppler-utils menyediakan pdftotext yang dipakai pdf-text-extract
RUN apt-get update \
 && apt-get install -y --no-install-recommends poppler-utils \
 && rm -rf /var/lib/apt/lists/* \
 && npm install -g pnpm@10

COPY package.json pnpm-lock.yaml pnpm-workspace.yaml ./
RUN pnpm install --frozen-lockfile

# Variabel NEXT_PUBLIC_* ditanam saat build, jadi harus diberikan lewat ARG
ARG NEXT_PUBLIC_POCKETBASE_URL=http://pocketbase:8090
ARG NEXT_PUBLIC_PB_URL=http://pocketbase:8090
ENV NEXT_PUBLIC_POCKETBASE_URL=$NEXT_PUBLIC_POCKETBASE_URL \
    NEXT_PUBLIC_PB_URL=$NEXT_PUBLIC_PB_URL

COPY . .
RUN OPENAI_API_KEY=build-placeholder \
    PB_ADMIN_EMAIL=build@placeholder.local \
    PB_ADMIN_PASSWORD=build-placeholder \
    ADMIN_API_KEY=build-placeholder \
    pnpm exec next build --webpack

ENV NODE_ENV=production \
    PDFTOTEXT_PATH=/usr/bin/pdftotext

EXPOSE 3000
CMD ["pnpm", "exec", "next", "start", "-H", "0.0.0.0", "-p", "3000"]

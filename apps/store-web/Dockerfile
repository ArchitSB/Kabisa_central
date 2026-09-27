FROM node:22-alpine AS builder
WORKDIR /workspace
RUN corepack enable && corepack prepare pnpm@10.14.0 --activate
COPY package.json pnpm-lock.yaml pnpm-workspace.yaml ./
COPY apps/admin-web/package.json apps/admin-web/package.json
COPY apps/store-web/package.json apps/store-web/package.json
COPY apps/mobile/package.json apps/mobile/package.json
COPY packages/core/package.json packages/core/package.json
COPY packages/api-client/package.json packages/api-client/package.json
COPY packages/design-tokens/package.json packages/design-tokens/package.json
COPY packages/ui-web/package.json packages/ui-web/package.json
COPY packages/shared/package.json packages/shared/package.json
RUN pnpm install --frozen-lockfile --filter @kabisa/store-web...
COPY packages packages
COPY apps/store-web apps/store-web
ARG VITE_STORE_API_URL=/api/v1/store
ENV VITE_STORE_API_URL=${VITE_STORE_API_URL}
RUN pnpm --filter @kabisa/store-web build

FROM nginxinc/nginx-unprivileged:1.27-alpine AS runtime
COPY apps/store-web/nginx.conf /etc/nginx/conf.d/default.conf
COPY apps/store-web/nginx-security.conf /etc/nginx/kabisa-security.conf
COPY --from=builder /workspace/apps/store-web/dist /usr/share/nginx/html
EXPOSE 8080

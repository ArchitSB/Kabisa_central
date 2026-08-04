FROM node:22-alpine AS builder

WORKDIR /workspace
RUN corepack enable && corepack prepare pnpm@10.14.0 --activate
COPY package.json pnpm-lock.yaml pnpm-workspace.yaml ./
COPY apps/admin-web/package.json apps/admin-web/package.json
COPY packages/shared/package.json packages/shared/package.json
RUN pnpm install --frozen-lockfile
COPY apps/admin-web apps/admin-web
COPY packages/shared packages/shared
ARG VITE_API_URL=/api/v1
ARG VITE_ENABLE_ROLE_SWITCHER=false
ENV VITE_API_URL=${VITE_API_URL} \
    VITE_ENABLE_ROLE_SWITCHER=${VITE_ENABLE_ROLE_SWITCHER}
RUN pnpm --filter @kabisa/admin-web build

FROM nginxinc/nginx-unprivileged:1.27-alpine AS runtime

COPY apps/admin-web/nginx.conf /etc/nginx/conf.d/default.conf
COPY --from=builder /workspace/apps/admin-web/dist /usr/share/nginx/html
EXPOSE 8080

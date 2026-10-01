# Builds the React frontend and bundles it into a Caddy image that also
# reverse-proxies /api to the backend. One container does TLS + static + proxy.
FROM node:22-alpine AS web
WORKDIR /app
COPY frontend/package.json ./
RUN npm install
COPY frontend/ ./
RUN npm run build

FROM caddy:2-alpine
COPY deploy/Caddyfile /etc/caddy/Caddyfile
COPY --from=web /app/dist/ /srv/www/

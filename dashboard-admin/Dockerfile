# Admin dashboard (Vite dev server) for local development.
FROM node:20-slim

WORKDIR /app

RUN corepack enable

COPY package.json ./
RUN pnpm install

COPY . .

EXPOSE 5174
CMD ["pnpm", "dev", "--host"]

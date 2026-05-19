# Production Dockerfile for Meeting Live frontend (Next.js)

# 1) Build stage
FROM node:20-alpine AS builder

WORKDIR /app

# Install deps first (to leverage Docker layer cache)
COPY package.json package-lock.json ./
RUN npm ci

# Copy source
COPY . .

# Build Next.js app
RUN npm run build

# 2) Runtime stage
FROM node:20-alpine AS runner

WORKDIR /app
ENV NODE_ENV=production

# Default backend endpoints (can be overridden at runtime)
# On Docker Desktop (Windows/macOS), host.docker.internal points to host machine
ENV NEXT_PUBLIC_WS_URL=ws://host.docker.internal:8765
ENV NEXT_PUBLIC_SIGNAL_URL=http://host.docker.internal:8081/offer

# Only copy necessary artifacts
COPY --from=builder /app/package.json /app/package-lock.json ./
COPY --from=builder /app/.next ./.next
COPY --from=builder /app/public ./public

RUN npm ci --omit=dev

EXPOSE 3000

CMD ["npm", "run", "start"]

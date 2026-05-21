# Production Dockerfile — MeetScribe Next.js frontend

FROM node:20-alpine AS builder

WORKDIR /app

ARG NEXT_PUBLIC_AUTH_API_URL=http://localhost:8200
ARG NEXT_PUBLIC_WS_URL=ws://localhost:8765
ARG NEXT_PUBLIC_SIGNAL_URL=http://localhost:8081/offer

ENV NEXT_PUBLIC_AUTH_API_URL=$NEXT_PUBLIC_AUTH_API_URL \
    NEXT_PUBLIC_WS_URL=$NEXT_PUBLIC_WS_URL \
    NEXT_PUBLIC_SIGNAL_URL=$NEXT_PUBLIC_SIGNAL_URL

COPY package.json package-lock.json ./
RUN npm ci

COPY . .
RUN npm run build

FROM node:20-alpine AS runner

WORKDIR /app
ENV NODE_ENV=production

COPY --from=builder /app/package.json /app/package-lock.json ./
COPY --from=builder /app/.next ./.next
COPY --from=builder /app/public ./public
COPY --from=builder /app/next.config.js ./next.config.js

RUN npm ci --omit=dev

EXPOSE 3000

CMD ["npm", "run", "start"]

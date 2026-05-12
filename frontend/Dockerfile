# Stage 1: Build
FROM node:20-alpine AS builder

WORKDIR /app

# Copy package files
COPY frontend/package.json frontend/package-lock.json ./

# Install dependencies
RUN npm ci

# Copy source code
COPY frontend/ .

# Build-time env vars for Next.js static generation
ARG NEXT_PUBLIC_KANSHAN_BACKEND_MODE=gateway
ARG NEXT_PUBLIC_KANSHAN_GATEWAY_URL=http://api-gateway:8000
ARG NEXT_PUBLIC_ZHIHU_ADAPTER_URL=http://zhihu-adapter:8070

ENV NEXT_PUBLIC_KANSHAN_BACKEND_MODE=$NEXT_PUBLIC_KANSHAN_BACKEND_MODE
ENV NEXT_PUBLIC_KANSHAN_GATEWAY_URL=$NEXT_PUBLIC_KANSHAN_GATEWAY_URL
ENV NEXT_PUBLIC_ZHIHU_ADAPTER_URL=$NEXT_PUBLIC_ZHIHU_ADAPTER_URL

# Build the app
RUN npm run build

# Stage 2: Runtime
FROM node:20-alpine

WORKDIR /app

# Copy built assets from builder
COPY --from=builder /app/.next ./.next
COPY --from=builder /app/public ./public
COPY --from=builder /app/node_modules ./node_modules
COPY --from=builder /app/package.json ./

EXPOSE 3000

CMD ["npm", "start"]

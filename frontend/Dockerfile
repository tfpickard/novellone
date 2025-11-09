FROM node:20-alpine AS builder
WORKDIR /app
COPY package*.json ./
RUN npm ci
COPY . .
RUN npm run build

FROM node:20-alpine
WORKDIR /app
COPY --from=builder /app/build ./build
COPY --from=builder /app/package*.json ./
RUN npm ci --production

# Railway provides PORT env var, default to 3000 for local dev
ENV PORT=3000
ENV HOST=0.0.0.0

EXPOSE 3000
CMD ["node", "build"]

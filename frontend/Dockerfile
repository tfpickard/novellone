FROM node:20-alpine AS builder
WORKDIR /app
COPY package*.json ./
RUN npm ci
COPY . .

# Accept build arguments for Vite environment variables
ARG VITE_PUBLIC_API_URL
ARG VITE_PUBLIC_WS_URL
ARG ORIGIN

# Set as environment variables during build
ENV VITE_PUBLIC_API_URL=$VITE_PUBLIC_API_URL
ENV VITE_PUBLIC_WS_URL=$VITE_PUBLIC_WS_URL
ENV ORIGIN=$ORIGIN

RUN npm run build

FROM node:20-alpine
WORKDIR /app
COPY --from=builder /app/build ./build
COPY --from=builder /app/package*.json ./
RUN npm ci --production


# Set port for production
ENV PORT=4000
ENV HOST=0.0.0.0

EXPOSE 4000

CMD ["node", "build"]

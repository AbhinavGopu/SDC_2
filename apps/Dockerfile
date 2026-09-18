FROM node:24-bookworm-slim AS build
WORKDIR /app
COPY package*.json ./
COPY citizen/package.json citizen/package.json
COPY planner/package.json planner/package.json
RUN npm ci
COPY . .
ARG APP
ENV API_INTERNAL_URL=http://api:8000
ENV NEXT_TELEMETRY_DISABLED=1
RUN npm run build --workspace=$APP
ENV APP_NAME=$APP
ENV NODE_ENV=production
ENV NEXT_TELEMETRY_DISABLED=1
EXPOSE 3000
CMD ["sh", "-c", "npm run start --workspace=$APP_NAME -- --hostname 0.0.0.0"]

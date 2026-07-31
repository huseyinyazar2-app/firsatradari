FROM node:22-alpine AS build

WORKDIR /app

COPY package.json package-lock.json ./
RUN npm install --global npm@11.6.2 \
    && npm ci

COPY . .

ARG VITE_FIRSAT_API_URL=/api
ENV VITE_FIRSAT_API_URL=$VITE_FIRSAT_API_URL

RUN npm run build \
    && npm prune --omit=dev --ignore-scripts --no-audit --no-fund

FROM node:22-alpine AS runtime

ENV NODE_ENV=production \
    PORT=3000

WORKDIR /app

COPY --from=build /app/package.json /app/package-lock.json ./
COPY --from=build /app/node_modules ./node_modules
COPY --from=build /app/dist ./dist

EXPOSE 3000

CMD ["npm", "run", "start"]

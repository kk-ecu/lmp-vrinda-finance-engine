FROM node:22-alpine
WORKDIR /app
COPY package.json .
RUN npm install
COPY . .
EXPOSE 3000
# VITE_PORT/VITE_API_TARGET are provided by compose; default to 3000 in-container.
CMD ["sh", "-c", "npm run dev -- --host 0.0.0.0 --port ${VITE_PORT:-3000}"]

# Stage 1: Build the application
FROM node:18-alpine AS builder

# Set working directory
WORKDIR /app
COPY package*.json ./

# Install ALL dependencies (including dev dependencies for build)
RUN npm install

# Copy source code
COPY . .

# Build args for Vite env vars
ARG VITE_API_BASE_URL=http://152.118.31.54:38003/api/v1
ARG VITE_API_BFF_URL=http://152.118.31.54:38003/api/v1
ARG VITE_SOCKET_IO_BASE_URL=http://152.118.31.54:38004
ARG VITE_SOCKET_BASE_URL=ws://152.118.31.54:38005
ARG VITE_SOCKET_ALTERNATIVE_BASE_URL=ws://152.118.31.54:38005
ENV VITE_API_BASE_URL=$VITE_API_BASE_URL
ENV VITE_API_BFF_URL=$VITE_API_BFF_URL
ENV VITE_SOCKET_IO_BASE_URL=$VITE_SOCKET_IO_BASE_URL
ENV VITE_SOCKET_BASE_URL=$VITE_SOCKET_BASE_URL
ENV VITE_SOCKET_ALTERNATIVE_BASE_URL=$VITE_SOCKET_ALTERNATIVE_BASE_URL

# Build the application
RUN npm run build

# Stage 2: Serve with Nginx
FROM nginx:alpine

# Copy custom nginx configuration
COPY nginx.conf /etc/nginx/nginx.conf

# Remove default nginx index page
RUN rm -rf /usr/share/nginx/html/*

# Copy built files from builder stage
COPY --from=builder /app/dist /usr/share/nginx/html

# Expose port 8004
EXPOSE 8004

# Start Nginx
ENTRYPOINT ["nginx", "-g", "daemon off;"]
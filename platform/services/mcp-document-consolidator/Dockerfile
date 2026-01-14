# Build stage
FROM node:20-slim AS builder

WORKDIR /app

# Install build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    python3 python3-pip make g++ \
    && rm -rf /var/lib/apt/lists/*

# Copy package files
COPY package.json package-lock.json* ./

# Install dependencies
RUN npm ci

# Copy source code
COPY . .

# Build TypeScript
RUN npm run build

# Production stage
FROM node:20-slim AS production

WORKDIR /app

# Install Python for embedding service
RUN apt-get update && apt-get install -y --no-install-recommends \
    python3 python3-pip python3-venv \
    && rm -rf /var/lib/apt/lists/*

# Create Python virtual environment
RUN python3 -m venv /app/venv
ENV PATH="/app/venv/bin:$PATH"

# Install Python dependencies (CPU-only torch for smaller image)
COPY python/requirements.txt /app/python/
RUN pip install --no-cache-dir torch --index-url https://download.pytorch.org/whl/cpu && \
    pip install --no-cache-dir -r /app/python/requirements.txt

# Copy Python service
COPY python/ /app/python/

# Copy package files and install production dependencies
COPY package.json package-lock.json* ./
RUN npm ci --omit=dev

# Copy built files from builder
COPY --from=builder /app/dist ./dist

# Create data directory
RUN mkdir -p /app/data

# Set environment variables
ENV NODE_ENV=production
ENV PYTHON_PATH=/app/venv/bin/python3

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
  CMD node -e "process.exit(0)" || exit 1

# Run as non-root user with home directory for HuggingFace cache
RUN groupadd -g 1001 nodejs && \
    useradd -m -u 1001 -g nodejs -d /home/nodejs nodejs && \
    chown -R nodejs:nodejs /app /home/nodejs

# Set HuggingFace cache directory
ENV HF_HOME=/home/nodejs/.cache/huggingface
ENV TRANSFORMERS_CACHE=/home/nodejs/.cache/huggingface

USER nodejs

# Start the server
CMD ["node", "dist/server.js"]

FROM python:3.11-slim

# System dependencies for pdfplumber / sentence-transformers
RUN apt-get update && apt-get install -y --no-install-recommends \
    libglib2.0-0 libgl1-mesa-glx gcc \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install Python dependencies first (layer caching)
COPY backend/requirements.txt ./requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Copy backend source
COPY backend/ ./backend/

# Copy .env if present (ignored in production — use env vars)
COPY .env* ./

EXPOSE 8000

# Download sentence-transformer model at build time so it's cached in the image
RUN python -c "from sentence_transformers import SentenceTransformer; SentenceTransformer('all-MiniLM-L6-v2')"

CMD ["uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "8000"]

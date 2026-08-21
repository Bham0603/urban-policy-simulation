# Backend (SUB-05) container. Single-stage, slim.
# Built with the project root as context to bundle the simulation dependency.
FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

# Copy simulation and backend codebases
COPY simulation ./simulation
COPY backend ./backend

# Install pip packages
RUN pip install --upgrade pip && \
    pip install ./simulation && \
    pip install ./backend

# Set workspace directory for the backend app runtime
WORKDIR /app/backend
RUN mkdir -p /app/backend/data

EXPOSE 8000

# Honor the platform's $PORT if provided, else default to 8000
CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}"]

FROM python:3.12-slim

WORKDIR /app

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app

# Install uv
RUN pip install --no-cache-dir uv

# Copy project files
COPY pyproject.toml uv.lock ./
COPY app/ ./app/
COPY run.py ./

# Create media directory
RUN mkdir -p media/images

# Install dependencies
RUN uv pip install --system

# Run the application
CMD ["python", "run.py"]

# Expose the port
EXPOSE 8000 
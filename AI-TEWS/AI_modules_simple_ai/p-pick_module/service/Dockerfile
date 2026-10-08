# Lightweight image for Docker-in-Docker (replaces rocm/dev-ubuntu-22.04)
FROM python:3.10-slim

ENV DEBIAN_FRONTEND=noninteractive
WORKDIR /app

# Disable OpenBLAS threading to avoid pthread_create failures in nested containers
ENV OPENBLAS_NUM_THREADS=1
# Use non-interactive matplotlib backend to avoid thread creation in FontManager
ENV MPLBACKEND=Agg

# Copy and install requirements (separated from dir copy to prevent multiple install on code changes)
COPY ./requirements.txt /app/requirements.txt
RUN pip install --progress-bar off --no-cache-dir -r requirements.txt

# Copy the current directory contents into the container at /app
COPY . /app

# Run terminal
CMD ["gunicorn", "--workers", "1", "--bind", "0.0.0.0:8000", "--timeout", "120", "pick_service:app"]

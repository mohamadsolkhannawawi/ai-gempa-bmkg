# Use the official ROCm image
FROM rocm/dev-ubuntu-22.04

# Set the working directory in the container
WORKDIR /app

# Install python
RUN apt-get update && \
    apt-get install -y python3 python3-pip

# Copy and install requirements (separated from dir copy to prevent multiple install on code changes)
COPY ./requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Copy the current directory contents into the container at /app
COPY . /app

# Run terminal
CMD ["gunicorn", "--workers", "3", "--bind", "0.0.0.0:8000", "pick_service:app"]

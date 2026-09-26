# Use the official ROCm image
FROM python:3.10-slim-bullseye

# Set the working directory in the container
WORKDIR /app

# Install unzip and give execution permission to data.sh
RUN apt-get update && apt-get install -y unzip procps && pip install gdown

RUN gdown https://drive.google.com/uc?id=1mu-74g_OTlGl9j730iBHRTDPz5HlMTtE
RUN gdown https://drive.google.com/uc?id=1kyjo_YxpodCfF9udnWvGdxhh0XUZQGuD

# Copy and install requirements (separated from dir copy to prevent multiple install on code changes)
COPY ./requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Copy the current directory contents into the container at /app
COPY . .

CMD ["uvicorn", "controller:app", "--host", "0.0.0.0", "--port", "8000"]

# CMD ["./data.sh"]

# # Run python when the container launches
# CMD ["python3", "-u", "starter.py"]

# # Run python when the container launches
# CMD ["python3", "-u", "player.py"]
FROM nvidia/cuda:12.1.0-runtime-ubuntu22.04

# Set non-interactive to prevent prompts during installation
ENV DEBIAN_FRONTEND=noninteractive

RUN apt-get update && apt-get install -y \
    python3.11 python3-pip python3.11-venv \
    libgl1-mesa-glx \
    libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Upgrade pip and install basic torch requirements
RUN python3.11 -m pip install --upgrade pip

COPY requirements.txt .

# Install dependencies
RUN python3.11 -m pip install -r requirements.txt

COPY . /app

# Expose FastAPI port
EXPOSE 8080

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8080", "--workers", "1"]

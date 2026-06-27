FROM python:3.9-slim

RUN apt-get update && apt-get install -y \
    gcc \
    python3-dev \
    gpiod \
    libgpiod-dev \
    && rm -rf /var/lib/apt/lists/*

RUN pip install --no-cache-dir adafruit-circuitpython-ads1x15 && \
    pip install --no-cache-dir --no-binary :all: rpi-lgpio

WORKDIR /app
COPY ct_reader.py .

CMD ["python", "-u", "ct_reader.py"]



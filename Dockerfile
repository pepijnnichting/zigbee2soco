FROM python:3.13-slim
RUN pip install --no-cache-dir --upgrade pip setuptools wheel
COPY requirements.txt requirements.txt
RUN pip install --no-cache-dir -r requirements.txt
COPY zigbee2soco.py /
ENV PYTHONUNBUFFERED=1
ENTRYPOINT ["python3", "/zigbee2soco.py"]

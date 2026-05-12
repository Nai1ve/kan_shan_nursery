FROM python:3.11-slim

WORKDIR /app

# Install shared-python package first
COPY packages/shared-python /app/packages/shared-python
RUN pip install --no-cache-dir /app/packages/shared-python

# Install service dependencies
COPY services/seed-service/requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r /app/requirements.txt

# Copy service code
COPY services/seed-service/app /app/app

EXPOSE 8030

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8030"]

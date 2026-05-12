FROM python:3.11-slim

WORKDIR /app

# Use China mirror for pip
RUN pip config set global.index-url https://pypi.tuna.tsinghua.edu.cn/simple

# Install shared-python package first
COPY packages/shared-python /app/packages/shared-python
RUN pip install --no-cache-dir /app/packages/shared-python

# Install service dependencies
COPY services/writing-service/requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r /app/requirements.txt

# Copy service code
COPY services/writing-service/app /app/app

EXPOSE 8050

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8050"]

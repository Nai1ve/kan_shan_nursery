FROM python:3.11-slim

WORKDIR /app

# Use China mirror for pip
RUN pip config set global.index-url https://pypi.tuna.tsinghua.edu.cn/simple

# Install shared-python package first
COPY packages/shared-python /app/packages/shared-python
RUN pip install --no-cache-dir /app/packages/shared-python

# Install service dependencies
COPY services/feedback-service/requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r /app/requirements.txt

# Copy service code
COPY services/feedback-service/app /app/app

EXPOSE 8060

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8060"]

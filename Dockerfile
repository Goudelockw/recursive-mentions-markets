FROM python:3.13-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
ENV PYTHONUNBUFFERED=1
# Railway service research-weekly (cron, Sunday night): checks, grading, calibration and a challenger refit.
# DATABASE_URL is the rmm_rw role: it can store challengers and ops rows, never change the live model.
CMD ["python", "-m", "rmm", "weekly", "--save", "--refit"]

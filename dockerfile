FROM python:3.10-slim

# poppler-utils（pdf2image）
RUN apt-get update && apt-get install -y poppler-utils

# Set working directory inside the container
WORKDIR /app

# Copy the dependency file and install Python packages
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy all project files into the container
COPY . .

# Default command to run the FastAPI app with Uvicorn
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]

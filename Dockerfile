FROM python:3.10-slim

# Set up working directory
WORKDIR /app

# Copy requirements first to leverage Docker cache
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application
COPY . .

# Make sure directory permissions are correct
RUN chmod -R 755 /app

# Expose the API port
EXPOSE 8182

# Run the FastAPI application
CMD ["python", "main.py"]

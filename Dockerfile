FROM python:3.10-slim

# Set up working directory
WORKDIR /app

# Copy requirements first to leverage Docker cache
COPY ./requirements.txt /app/requirements.txt
RUN pip install -r requirements.txt

# Copy all application app
COPY ./main.py /app/
COPY ./config.py /app/
COPY ./database/ /app/database/
COPY ./models/ /app/models/
COPY ./services/ /app/services/
COPY ./utils/ /app/utils/

# Alternative: Copy the entire project directory
# COPY . /app/

# Make sure directory permissions are correct
RUN chmod -R 755 /app

# Expose the API port
EXPOSE 8182

# Run the FastAPI application
ENTRYPOINT ["python3", "main.py"]
# Use an official Python runtime as the base image
FROM python:3.11-slim

# Set the working directory inside the container
WORKDIR /app

# Copy the dependencies file to the working directory
COPY requirements.txt .

# Install the dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy the entire project into the container
COPY . .

# Install diagnostic_analyzer_package as a Python package
RUN pip install .

# Copy the .env file to the working directory
COPY .env .env

# Expose the port your application will run on (e.g., 8000 for Flask/Django)
EXPOSE 8000

# Command to run your application
CMD ["python", "web_app/app.py"]
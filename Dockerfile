# # Use an official Python runtime as the base image
# FROM python:3.11-slim

# # Set the working directory inside the container
# WORKDIR /app

# # Copy the dependencies file to the working directory
# COPY requirements.txt .

# # Install the dependencies
# RUN pip install --no-cache-dir -r requirements.txt

# # Copy the entire project into the container
# COPY . .

# # Install diagnostic_analyzer_package as a Python package
# RUN pip install .

# # Copy the .env file to the working directory
# COPY .env .env

# # Expose the port your application will run on (e.g., 8000 for Flask/Django)
# EXPOSE 8000

# # Command to run your application
# CMD ["python", "diagnostic_analyzer_package/app.py"]

# Stage 1: Build React frontend
FROM node:20-alpine AS frontend-build
WORKDIR /frontend
COPY frontend/package*.json ./
RUN npm install
COPY frontend/ ./
RUN npm run build

# Stage 2: Build backend and final image
FROM python:3.11-slim

# Set workdir
WORKDIR /app

# Install requirements (first to cache)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy backend code
COPY diagnostic_analyzer_package/ ./diagnostic_analyzer_package/

# Copy setup.py so we can pip install our package
COPY setup.py .

# Install our package (as editable, so imports work)
RUN pip install .

# Copy frontend build into Flask's static folder
COPY --from=frontend-build /frontend/build ./diagnostic_analyzer_package/frontend/build

# Copy .env 
COPY .env .env

# Expose port
EXPOSE 8000

# Start with gunicorn
CMD ["gunicorn", "-b", "0.0.0.0:8000", "diagnostic_analyzer_package.app:app"]

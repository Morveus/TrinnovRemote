# Use the official Python image from the Docker Hub
FROM python:3.9

# Set the working directory
WORKDIR /app

# Copy the current directory contents into the container
ADD . /app

# Install the required packages
RUN pip install Flask websockets

# Make port 5555 available to the world outside this container
EXPOSE 5555

# Run the application
CMD ["python", "app.py"]

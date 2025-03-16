#!/bin/bash

# Make all files in the repository executable
chmod -R +x .

echo "All files are now executable."

# Check if Docker is installed
if ! command -v docker &> /dev/null; then
    echo "Docker is not installed. Please install Docker and try again."
    exit 1
fi

echo "Docker is installed. Proceeding with setup."

# Create a Dockerfile if it doesn't exist
DOCKERFILE="Dockerfile"
if [ ! -f "$DOCKERFILE" ]; then
    cat <<EOF > "$DOCKERFILE"
    FROM python:3.10-slim
    
    WORKDIR /app
    
    COPY . /app
    
    RUN pip install --no-cache-dir \
        requests \
        json \
        urllib3 \
        pandas \
        os \
        csv \
        numpy \
        pytz \
        logging \
        python-dotenv \

    CMD ["/bin/bash"]
EOF
    echo "Dockerfile created."
fi

# Build the Docker image
docker build -t my_python_env .

echo "Docker image built successfully. You can run the container with:"
echo "docker run -it --rm my_python_env"

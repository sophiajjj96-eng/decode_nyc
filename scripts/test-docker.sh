#!/bin/bash
# Local Docker Test - Verify container works before Cloud Run deployment

set -e

echo "=== Testing Docker Image Locally ==="
echo ""

# Check if in correct directory
if [ ! -f "Dockerfile" ]; then
  echo "Error: Must run from algorithm-explained directory"
  echo "Run: cd algorithm-explained && ./scripts/test-docker.sh"
  exit 1
fi

# Build image
echo "Building Docker image..."
docker build -t algorithm-explained:test .
echo "✓ Image built"
echo ""

# Check for API key
if [ -z "$GOOGLE_API_KEY" ]; then
  echo "Warning: GOOGLE_API_KEY not set"
  echo "For local testing, export GOOGLE_API_KEY before running"
  echo ""
  echo "Run the container with:"
  echo "  docker run -p 8080:8080 \\"
  echo "    -e GOOGLE_API_KEY=your_key \\"
  echo "    -e GOOGLE_GENAI_USE_VERTEXAI=FALSE \\"
  echo "    algorithm-explained:test"
  echo ""
  exit 0
fi

# Run container
echo "Starting container on port 8080..."
docker run -d \
  --name algorithm-explained-test \
  -p 8080:8080 \
  -e GOOGLE_API_KEY=$GOOGLE_API_KEY \
  -e GOOGLE_GENAI_USE_VERTEXAI=FALSE \
  algorithm-explained:test

echo "✓ Container started"
echo ""

# Wait for startup
echo "Waiting for service to start..."
sleep 5

# Test health endpoint
echo "Testing health endpoint..."
curl -f http://localhost:8080/health || {
  echo "✗ Health check failed"
  docker logs algorithm-explained-test
  docker stop algorithm-explained-test
  docker rm algorithm-explained-test
  exit 1
}

echo ""
echo "✓ Health check passed"
echo ""
echo "=== Container running successfully ==="
echo ""
echo "Test in browser: open http://localhost:8080"
echo ""
echo "View logs: docker logs -f algorithm-explained-test"
echo ""
echo "When done, cleanup:"
echo "  docker stop algorithm-explained-test"
echo "  docker rm algorithm-explained-test"
echo ""

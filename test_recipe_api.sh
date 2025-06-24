#!/bin/bash

# First, let's sign in to get a token
echo "Signing in..."
RESPONSE=$(curl -s -X POST http://localhost:8000/v1/auth/signin \
  -H "Content-Type: application/json" \
  -d '{
    "email": "testapi@example.com",
    "password": "password123"
  }')

# Extract the access token
TOKEN=$(echo $RESPONSE | python3 -c "import sys, json; print(json.load(sys.stdin)['access_token'])")

if [ -z "$TOKEN" ]; then
  echo "Failed to get token. Response:"
  echo $RESPONSE
  exit 1
fi

echo "Got token: ${TOKEN:0:20}..."

# Now try to create a recipe
echo -e "\nCreating recipe..."
curl -X POST http://localhost:8000/v1/recipes \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $TOKEN" \
  -d '{
    "title": "",
    "yield": "1 serving",
    "ingredients": [],
    "steps": []
  }' -v
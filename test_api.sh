#!/bin/bash

# Script para testar a API de análise de vídeos

API_URL="http://localhost:8000"
API_PREFIX="/api/v1"

echo "🎯 Video Analysis API - Test Script"
echo "===================================="
echo ""

# 1. Health Check
echo "1️⃣  Health Check..."
echo "GET $API_URL/health"
curl -s "$API_URL/health" | jq .
echo ""
echo ""

# 2. Listar vídeos disponíveis
echo "2️⃣  Listing available videos..."
echo "GET $API_URL$API_PREFIX/videos"
curl -s "$API_URL$API_PREFIX/videos" | jq .
echo ""
echo ""

# 3. Submeter vídeo para análise
echo "3️⃣  Submitting video for analysis..."
echo "POST $API_URL$API_PREFIX/jobs"
RESPONSE=$(curl -s -X POST "$API_URL$API_PREFIX/jobs" \
  -H "Content-Type: application/json" \
  -d '{
    "video_url": "http://localhost:8000/api/v1/videos/sample.mp4",
    "options": {
      "analysis_depth": "detailed",
      "include_timestamps": true,
      "language": "pt-BR",
      "extract_entities": true,
      "detect_sentiment": false
    }
  }')

echo "$RESPONSE" | jq .

# Extrai job_id
JOB_ID=$(echo "$RESPONSE" | jq -r '.job_id')
echo ""
echo "📝 Job ID: $JOB_ID"
echo ""

# 4. Consultar status em loop
echo "4️⃣  Checking job status (will check 10 times with 3s delay)..."
for i in {1..10}; do
  echo ""
  echo "Attempt $i/10..."
  STATUS_RESPONSE=$(curl -s "$API_URL$API_PREFIX/jobs/$JOB_ID")
  STATUS=$(echo "$STATUS_RESPONSE" | jq -r '.status')
  echo "Status: $STATUS"

  if [ "$STATUS" = "completed" ]; then
    echo ""
    echo "✅ Analysis completed!"
    echo "$STATUS_RESPONSE" | jq .
    break
  elif [ "$STATUS" = "failed" ]; then
    echo ""
    echo "❌ Analysis failed!"
    echo "$STATUS_RESPONSE" | jq .
    break
  else
    echo "⏳ Still processing... (waiting 3s)"
    sleep 3
  fi
done

echo ""
echo ""
echo "5️⃣  List all jobs..."
echo "GET $API_URL$API_PREFIX/jobs"
curl -s "$API_URL$API_PREFIX/jobs" | jq .

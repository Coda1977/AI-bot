#!/bin/bash
# Startup script for Railway deployment

echo "Starting Management Knowledge RAG API..."
echo "Installing dependencies..."
pip install -r requirements_rag.txt

echo "Starting FastAPI server..."
python rag_api.py
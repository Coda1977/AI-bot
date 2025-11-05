#!/usr/bin/env python3
"""
Vercel-optimized RAG API Service for Management Knowledge Base
Adapted for serverless deployment
"""

import json
import os
import logging
from typing import Dict, List, Optional, Any
from pathlib import Path

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
import chromadb
from chromadb.config import Settings
import anthropic
import openai

# Configure logging for Vercel
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize FastAPI app
app = FastAPI(
    title="Management Knowledge RAG API",
    description="Semantic search and AI responses for management frameworks and guidance",
    version="1.0.0"
)

# Add CORS middleware for Custom GPT Actions
app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://chat.openai.com", "https://chatgpt.com"],
    allow_credentials=True,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["*"],
)

# Pydantic models for API requests/responses
class SearchRequest(BaseModel):
    query: str = Field(..., description="Search query for management knowledge")
    domain: Optional[str] = Field(None, description="Management domain filter", enum=["coaching", "feedback", "delegation", "performance", "leadership", "communication"])
    detail_level: Optional[str] = Field("detailed", description="Response detail level", enum=["quick", "detailed", "comprehensive"])
    max_results: Optional[int] = Field(5, description="Maximum number of search results", ge=1, le=20)

class SearchResult(BaseModel):
    content: str
    source_file: str
    relevance_score: float
    metadata: Dict[str, Any]

class SearchResponse(BaseModel):
    results: List[SearchResult]
    query: str
    total_results: int

class AskRequest(BaseModel):
    query: str = Field(..., description="Question about management")
    domain: Optional[str] = Field(None, description="Management domain filter")
    detail_level: Optional[str] = Field("detailed", description="Response detail level")
    context_size: Optional[int] = Field(5, description="Number of knowledge chunks to use", ge=1, le=10)

class AskResponse(BaseModel):
    answer: str
    sources: List[SearchResult]
    query: str
    ai_provider: str

# Global variables for clients and database
_chroma_client = None
_collection = None
_anthropic_client = None
_openai_client = None
_chunks_data = None

def get_clients():
    """Initialize and return clients (singleton pattern for serverless)"""
    global _chroma_client, _collection, _anthropic_client, _openai_client, _chunks_data

    if _chroma_client is None:
        try:
            # Initialize ChromaDB in memory for serverless
            _chroma_client = chromadb.Client(
                Settings(
                    anonymized_telemetry=False,
                    is_persistent=False
                )
            )
            logger.info("ChromaDB client initialized")
        except Exception as e:
            logger.error(f"Error initializing ChromaDB: {e}")
            raise HTTPException(status_code=500, detail="Database initialization failed")

    if _anthropic_client is None and os.getenv("ANTHROPIC_API_KEY"):
        try:
            _anthropic_client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
            logger.info("Anthropic client initialized")
        except Exception as e:
            logger.error(f"Error initializing Anthropic: {e}")

    if _openai_client is None and os.getenv("OPENAI_API_KEY"):
        try:
            _openai_client = openai.OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
            logger.info("OpenAI client initialized")
        except Exception as e:
            logger.error(f"Error initializing OpenAI: {e}")

    return _chroma_client, _collection, _anthropic_client, _openai_client

def load_knowledge_base():
    """Load knowledge base from JSON file"""
    global _collection, _chunks_data

    chroma_client, collection, anthropic_client, openai_client = get_clients()

    if _collection is not None:
        return _collection

    try:
        # Load chunks data if not already loaded
        if _chunks_data is None:
            # In Vercel, files are in the root directory
            chunks_file = Path("chunks_data.json")
            if not chunks_file.exists():
                # Try alternative path
                chunks_file = Path("output/chromadb_data/chunks_data.json")
                if not chunks_file.exists():
                    raise HTTPException(status_code=500, detail="Knowledge base file not found")

            with open(chunks_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            _chunks_data = data.get('chunks', [])
            logger.info(f"Loaded {len(_chunks_data)} chunks from JSON")

        if not _chunks_data:
            raise HTTPException(status_code=500, detail="No chunks found in knowledge base")

        # Create ChromaDB collection
        _collection = chroma_client.get_or_create_collection(
            name="management_knowledge",
            metadata={"description": "Management frameworks and guidance"}
        )

        # Prepare data for ChromaDB
        ids = []
        documents = []
        metadatas = []

        for chunk in _chunks_data:
            ids.append(chunk['id'])
            documents.append(chunk['content'])
            metadatas.append(chunk['metadata'])

        # Add to ChromaDB in batches (smaller for serverless)
        batch_size = 50
        for i in range(0, len(ids), batch_size):
            batch_ids = ids[i:i+batch_size]
            batch_docs = documents[i:i+batch_size]
            batch_metadata = metadatas[i:i+batch_size]

            _collection.add(
                ids=batch_ids,
                documents=batch_docs,
                metadatas=batch_metadata
            )

        logger.info(f"Loaded {len(_chunks_data)} chunks into ChromaDB")
        return _collection

    except Exception as e:
        logger.error(f"Error loading knowledge base: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to load knowledge base: {str(e)}")

@app.get("/api", response_model=Dict[str, str])
async def root():
    """Health check endpoint"""
    return {
        "status": "running",
        "service": "Management Knowledge RAG API",
        "version": "1.0.0",
        "platform": "Vercel"
    }

@app.get("/api/health")
async def health_check():
    """Detailed health check"""
    try:
        collection = load_knowledge_base()
        chroma_client, _, anthropic_client, openai_client = get_clients()

        health_status = {
            "status": "healthy",
            "chromadb": collection is not None,
            "anthropic": anthropic_client is not None,
            "openai": openai_client is not None,
            "knowledge_base_size": collection.count() if collection else 0,
            "platform": "Vercel"
        }
        return health_status
    except Exception as e:
        logger.error(f"Health check error: {e}")
        return {
            "status": "error",
            "error": str(e),
            "platform": "Vercel"
        }

@app.post("/api/search", response_model=SearchResponse)
async def search_knowledge(request: SearchRequest):
    """Search the knowledge base for relevant content"""
    try:
        collection = load_knowledge_base()

        # Perform semantic search
        results = collection.query(
            query_texts=[request.query],
            n_results=request.max_results,
            include=["documents", "metadatas", "distances"]
        )

        # Format results
        search_results = []
        for i, (doc, metadata, distance) in enumerate(zip(
            results['documents'][0],
            results['metadatas'][0],
            results['distances'][0]
        )):
            search_results.append(SearchResult(
                content=doc,
                source_file=metadata.get('source_file', 'Unknown'),
                relevance_score=1.0 - distance,  # Convert distance to relevance score
                metadata=metadata
            ))

        return SearchResponse(
            results=search_results,
            query=request.query,
            total_results=len(search_results)
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Search error: {e}")
        raise HTTPException(status_code=500, detail=f"Search failed: {str(e)}")

@app.post("/api/ask", response_model=AskResponse)
async def ask_question(request: AskRequest):
    """Ask a question and get an AI-powered response with sources"""
    try:
        collection = load_knowledge_base()
        chroma_client, _, anthropic_client, openai_client = get_clients()

        # First, search for relevant context
        search_results = collection.query(
            query_texts=[request.query],
            n_results=request.context_size,
            include=["documents", "metadatas", "distances"]
        )

        # Prepare context for AI
        context_chunks = []
        sources = []

        for doc, metadata, distance in zip(
            search_results['documents'][0],
            search_results['metadatas'][0],
            search_results['distances'][0]
        ):
            context_chunks.append(doc)
            sources.append(SearchResult(
                content=doc,
                source_file=metadata.get('source_file', 'Unknown'),
                relevance_score=1.0 - distance,
                metadata=metadata
            ))

        # Create prompt for AI
        context_text = "\n\n---\n\n".join(context_chunks)

        prompt = f"""You are an expert management consultant. Use the provided management knowledge to answer the question with specific, actionable advice.

CONTEXT FROM MANAGEMENT KNOWLEDGE BASE:
{context_text}

QUESTION: {request.query}

Please provide a comprehensive answer that:
1. Gives specific, actionable advice
2. References relevant frameworks from the knowledge base
3. Includes practical next steps
4. Maintains a professional consulting tone

If the question is outside management topics, politely redirect to management-related guidance.

ANSWER:"""

        # Get AI response
        ai_provider = "none"

        if anthropic_client:
            try:
                response = anthropic_client.messages.create(
                    model="claude-3-5-sonnet-20241022",
                    max_tokens=1000,
                    messages=[{"role": "user", "content": prompt}]
                )
                answer = response.content[0].text
                ai_provider = "anthropic"
            except Exception as e:
                logger.error(f"Anthropic API error: {e}")
                # Fall back to OpenAI if available
                if openai_client:
                    anthropic_client = None
                else:
                    raise HTTPException(status_code=500, detail="AI service unavailable")

        if openai_client and ai_provider == "none":
            try:
                response = openai_client.chat.completions.create(
                    model="gpt-4",
                    messages=[{"role": "user", "content": prompt}],
                    max_tokens=1000,
                    temperature=0.7
                )
                answer = response.choices[0].message.content
                ai_provider = "openai"
            except Exception as e:
                logger.error(f"OpenAI API error: {e}")
                raise HTTPException(status_code=500, detail="AI service unavailable")

        if ai_provider == "none":
            raise HTTPException(status_code=500, detail="No AI provider available")

        return AskResponse(
            answer=answer,
            sources=sources,
            query=request.query,
            ai_provider=ai_provider
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Ask question error: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to generate response: {str(e)}")

# For Vercel compatibility
handler = app
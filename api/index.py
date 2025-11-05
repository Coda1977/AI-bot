#!/usr/bin/env python3
"""
Pinecone RAG API v2.0 - Updated for 2025 API
Uses current Pinecone SDK with integrated embeddings and modern patterns
"""
import json
import os
import logging
from typing import Dict, List, Optional, Any
from pathlib import Path
import time

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import uvicorn

# Global variables for caching
_pinecone_client = None
_pinecone_index = None
_anthropic_client = None
_openai_client = None
_knowledge_loaded = False

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Pydantic models
class SearchRequest(BaseModel):
    query: str
    top_k: int = 5
    namespace: str = "management-knowledge"

class SearchResult(BaseModel):
    id: str
    content: str
    metadata: Dict[str, Any]
    score: float

class SearchResponse(BaseModel):
    results: List[SearchResult]
    total_results: int
    query: str

class AskRequest(BaseModel):
    question: str
    top_k: int = 5
    ai_provider: Optional[str] = None
    namespace: str = "management-knowledge"

class AskResponse(BaseModel):
    answer: str
    sources: List[SearchResult]
    ai_provider: str
    question: str

# Initialize FastAPI app
app = FastAPI(
    title="Management Knowledge RAG API v2.0",
    description="Current Pinecone API (2025) with integrated embeddings for management knowledge",
    version="2.0.0"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

def get_pinecone_client():
    """Initialize Pinecone client using current 2025 API"""
    global _pinecone_client
    if _pinecone_client is None:
        try:
            from pinecone import Pinecone  # Current 2025 import
            api_key = os.getenv('PINECONE_API_KEY')
            if not api_key:
                raise ValueError("PINECONE_API_KEY environment variable not set")
            _pinecone_client = Pinecone(api_key=api_key)
            logger.info("Pinecone client initialized with 2025 API")
        except Exception as e:
            logger.error(f"Failed to initialize Pinecone client: {e}")
            raise HTTPException(status_code=500, detail=f"Pinecone initialization failed: {e}")
    return _pinecone_client

def get_pinecone_index():
    """Get Pinecone index using current 2025 API"""
    global _pinecone_index
    if _pinecone_index is None:
        try:
            client = get_pinecone_client()
            index_name = os.getenv('PINECONE_INDEX_NAME', 'management-knowledge-v2')
            _pinecone_index = client.Index(index_name)
            logger.info(f"Connected to Pinecone index: {index_name}")
        except Exception as e:
            logger.error(f"Failed to connect to Pinecone index: {e}")
            raise HTTPException(status_code=500, detail=f"Pinecone index connection failed: {e}")
    return _pinecone_index

def get_anthropic_client():
    """Initialize Anthropic client"""
    global _anthropic_client
    if _anthropic_client is None:
        try:
            import anthropic
            api_key = os.getenv('ANTHROPIC_API_KEY')
            if api_key:
                _anthropic_client = anthropic.Anthropic(api_key=api_key)
                logger.info("Anthropic client initialized")
            else:
                logger.warning("ANTHROPIC_API_KEY not found")
        except Exception as e:
            logger.error(f"Failed to initialize Anthropic client: {e}")
    return _anthropic_client

def get_openai_client():
    """Initialize OpenAI client"""
    global _openai_client
    if _openai_client is None:
        try:
            import openai
            api_key = os.getenv('OPENAI_API_KEY')
            if api_key:
                _openai_client = openai.OpenAI(api_key=api_key)
                logger.info("OpenAI client initialized")
            else:
                logger.warning("OPENAI_API_KEY not found")
        except Exception as e:
            logger.error(f"Failed to initialize OpenAI client: {e}")
    return _openai_client

async def ensure_knowledge_loaded():
    """Ensure knowledge base is loaded into Pinecone using 2025 API"""
    global _knowledge_loaded
    if _knowledge_loaded:
        return

    try:
        # Check if index has data
        index = get_pinecone_index()
        stats = index.describe_index_stats()
        namespace = os.getenv('PINECONE_NAMESPACE', 'management-knowledge')

        # Check if our namespace has data
        namespace_stats = stats.namespaces.get(namespace, {})
        if namespace_stats.get('vector_count', 0) > 0:
            logger.info(f"Knowledge base already loaded: {namespace_stats.get('vector_count')} vectors in namespace '{namespace}'")
            _knowledge_loaded = True
            return

        # Load knowledge base from file
        knowledge_file = Path("output/chromadb_data/chunks_data.json")
        if not knowledge_file.exists():
            # Try alternative paths
            alt_paths = [
                Path("../output/chromadb_data/chunks_data.json"),
                Path("chunks_data.json"),
            ]
            for alt_path in alt_paths:
                if alt_path.exists():
                    knowledge_file = alt_path
                    break
            else:
                raise HTTPException(status_code=500, detail="Knowledge base file not found")

        logger.info(f"Loading knowledge base from: {knowledge_file}")
        with open(knowledge_file, 'r', encoding='utf-8') as f:
            data = json.load(f)

        chunks = data.get('chunks', [])
        if not chunks:
            raise HTTPException(status_code=500, detail="No chunks found in knowledge base")

        logger.info(f"Processing {len(chunks)} chunks for Pinecone upload using 2025 API")

        # Prepare records for new API format
        records = []
        for chunk in chunks:
            # Prepare metadata (keep essential fields)
            metadata = {
                'source_file': chunk['metadata'].get('source_file', 'Unknown'),
                'framework': chunk['metadata'].get('framework', 'Unknown'),
                'category': chunk['metadata'].get('category', 'General'),
                'section': chunk['metadata'].get('section', ''),
                'chunk_type': chunk['metadata'].get('chunk_type', 'unknown'),
                'word_count': chunk.get('word_count', 0),
                'language': chunk['metadata'].get('language', 'unknown')
            }

            # Create record in new format
            records.append({
                '_id': chunk['id'],
                'content': chunk['content'],  # This will be embedded automatically
                **metadata
            })

        # Upload in batches using new upsert_records method
        batch_size = 100
        total_uploaded = 0

        for i in range(0, len(records), batch_size):
            batch = records[i:i + batch_size]

            try:
                # Use new upsert_records method with namespace
                index.upsert_records(namespace, batch)
                total_uploaded += len(batch)
                logger.info(f"Uploaded batch {i//batch_size + 1}: {total_uploaded}/{len(records)} records")

                # Add small delay to avoid rate limits
                time.sleep(1)

            except Exception as e:
                logger.error(f"Failed to upload batch {i//batch_size + 1}: {e}")
                continue

        logger.info(f"Successfully uploaded {total_uploaded} records to Pinecone namespace '{namespace}'")

        # Wait for indexing
        logger.info("Waiting 10 seconds for indexing to complete...")
        time.sleep(10)

        _knowledge_loaded = True

    except Exception as e:
        logger.error(f"Failed to load knowledge base: {e}")
        raise HTTPException(status_code=500, detail=f"Knowledge base loading failed: {e}")

@app.get("/api/health")
async def health_check():
    """Health check endpoint"""
    try:
        # Check Pinecone connection
        index = get_pinecone_index()
        stats = index.describe_index_stats()
        namespace = os.getenv('PINECONE_NAMESPACE', 'management-knowledge')

        # Check AI providers
        anthropic_available = get_anthropic_client() is not None
        openai_available = get_openai_client() is not None

        # Get namespace stats
        namespace_stats = stats.namespaces.get(namespace, {})

        return {
            "status": "healthy",
            "service": "Management Knowledge RAG API v2.0",
            "version": "2.0.0",
            "api_version": "2025",
            "pinecone": {
                "connected": True,
                "total_vectors": stats.total_vector_count,
                "namespace": namespace,
                "namespace_vectors": namespace_stats.get('vector_count', 0),
                "index_name": os.getenv('PINECONE_INDEX_NAME', 'management-knowledge-v2'),
                "embedding_model": "integrated (llama-text-embed-v2 or similar)"
            },
            "ai_providers": {
                "anthropic": anthropic_available,
                "openai": openai_available,
                "preferred": os.getenv('PREFERRED_AI_PROVIDER', 'anthropic')
            },
            "knowledge_loaded": _knowledge_loaded
        }
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return {
            "status": "unhealthy",
            "error": str(e),
            "api_version": "2025"
        }

@app.post("/api/search", response_model=SearchResponse)
async def search_knowledge(request: SearchRequest):
    """Search the management knowledge base using 2025 API"""
    try:
        await ensure_knowledge_loaded()

        # Use new search API format
        index = get_pinecone_index()

        # Search using current 2025 API
        search_results = index.search(
            namespace=request.namespace,
            query={
                "top_k": request.top_k,
                "inputs": {
                    "text": request.query
                }
            }
        )

        # Process results from new API format
        results = []
        hits = search_results.get('result', {}).get('hits', [])

        for hit in hits:
            results.append(SearchResult(
                id=hit['_id'],
                content=hit['fields'].get('content', ''),
                metadata={
                    'source_file': hit['fields'].get('source_file', 'Unknown'),
                    'framework': hit['fields'].get('framework', 'Unknown'),
                    'category': hit['fields'].get('category', 'General'),
                    'section': hit['fields'].get('section', ''),
                    'word_count': hit['fields'].get('word_count', 0)
                },
                score=float(hit['_score'])
            ))

        return SearchResponse(
            results=results,
            total_results=len(results),
            query=request.query
        )

    except Exception as e:
        logger.error(f"Search failed: {e}")
        raise HTTPException(status_code=500, detail=f"Search failed: {e}")

@app.post("/api/ask", response_model=AskResponse)
async def ask_question(request: AskRequest):
    """Ask a question and get an AI-powered response with sources"""
    try:
        # First, search for relevant context
        search_request = SearchRequest(
            query=request.question,
            top_k=request.top_k,
            namespace=request.namespace
        )
        search_response = await search_knowledge(search_request)

        if not search_response.results:
            raise HTTPException(status_code=404, detail="No relevant knowledge found for this question")

        # Prepare context from search results
        context_parts = []
        for i, result in enumerate(search_response.results, 1):
            source_info = f"Source {i} ({result.metadata.get('source_file', 'Unknown')})"
            context_parts.append(f"{source_info}:\n{result.content}\n")

        context = "\n---\n".join(context_parts)

        # Determine AI provider
        preferred_provider = request.ai_provider or os.getenv('PREFERRED_AI_PROVIDER', 'anthropic')

        # Generate AI response
        if preferred_provider == 'anthropic':
            answer = await generate_anthropic_response(request.question, context)
            used_provider = 'anthropic'
        else:
            answer = await generate_openai_response(request.question, context)
            used_provider = 'openai'

        return AskResponse(
            answer=answer,
            sources=search_response.results,
            ai_provider=used_provider,
            question=request.question
        )

    except Exception as e:
        logger.error(f"Ask question failed: {e}")
        raise HTTPException(status_code=500, detail=f"Question processing failed: {e}")

async def generate_anthropic_response(question: str, context: str) -> str:
    """Generate response using Anthropic Claude"""
    try:
        client = get_anthropic_client()
        if not client:
            raise Exception("Anthropic client not available")

        prompt = f"""You are a senior management consultant with deep expertise in leadership, feedback, coaching, and organizational effectiveness. You have access to a comprehensive knowledge base of management frameworks and best practices.

Based on the provided context from management resources, provide a professional, actionable response to the user's question. Your response should:

1. Be practical and immediately actionable
2. Reference specific frameworks or methodologies when relevant
3. Use a professional consulting tone
4. Cite sources when appropriate
5. Be concise but comprehensive

Context from knowledge base:
{context}

Question: {question}

Provide a professional management consultant response:"""

        response = client.messages.create(
            model="claude-3-sonnet-20240229",
            max_tokens=1500,
            messages=[{"role": "user", "content": prompt}]
        )

        return response.content[0].text

    except Exception as e:
        logger.error(f"Anthropic response generation failed: {e}")
        # Fallback to OpenAI
        return await generate_openai_response(question, context)

async def generate_openai_response(question: str, context: str) -> str:
    """Generate response using OpenAI GPT"""
    try:
        client = get_openai_client()
        if not client:
            raise Exception("OpenAI client not available")

        response = client.chat.completions.create(
            model="gpt-4",
            messages=[
                {
                    "role": "system",
                    "content": "You are a senior management consultant with deep expertise in leadership, feedback, coaching, and organizational effectiveness. Provide professional, actionable advice based on the provided management knowledge base context."
                },
                {
                    "role": "user",
                    "content": f"""Based on this context from management resources:

{context}

Question: {question}

Provide a professional management consultant response that is practical, actionable, and references relevant frameworks when appropriate."""
                }
            ],
            max_tokens=1500,
            temperature=0.7
        )

        return response.choices[0].message.content

    except Exception as e:
        logger.error(f"OpenAI response generation failed: {e}")
        return "I apologize, but I'm unable to generate a response at this time. Please try again later."

# Main entry point for Vercel
if __name__ == "__main__":
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
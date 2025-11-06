#!/usr/bin/env python3
"""
Knowledge Service API v4.0 - Proper Architecture
- Loads chunks ONCE at startup (not on every request)
- Keeps data in memory for fast access
- No fake embeddings
- Multi-tenant namespace support
- Simple API: question → sources
"""
import json
import os
import logging
import gzip
import base64
from typing import Dict, List, Optional, Any
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Global in-memory knowledge base (loaded ONCE at startup)
_knowledge_base: Dict[str, List[Dict]] = {}
_knowledge_loaded = False

# Pydantic models
class SearchRequest(BaseModel):
    query: str
    top_k: int = 5
    namespace: str = "management-knowledge"  # For multi-tenancy

class SearchResult(BaseModel):
    id: str
    content: str
    metadata: Dict[str, Any]
    score: float

class SearchResponse(BaseModel):
    results: List[SearchResult]
    total_results: int
    query: str
    namespace: str

class AskRequest(BaseModel):
    question: str
    top_k: int = 5
    namespace: str = "management-knowledge"

class AskResponse(BaseModel):
    answer: str
    sources: List[SearchResult]
    question: str
    namespace: str

# Initialize FastAPI app
app = FastAPI(
    title="Management Knowledge Service API v4.0",
    description="Efficient knowledge service - loads data once, searches fast",
    version="4.0.0"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def load_chunks_once() -> Dict[str, List[Dict]]:
    """
    Load all knowledge base chunks ONCE at startup and keep in memory.
    Returns dict mapping namespace -> list of chunks
    """
    global _knowledge_loaded

    if _knowledge_loaded:
        logger.info("Knowledge base already loaded")
        return _knowledge_base

    try:
        # Try embedded base64 first (for Vercel)
        try:
            from api.embedded_chunks import CHUNKS_DATA_B64
            logger.info("Loading from embedded base64 data")
            gzipped_data = base64.b64decode(CHUNKS_DATA_B64)
            data = json.loads(gzip.decompress(gzipped_data).decode('utf-8'))
        except ImportError:
            # Try local file system
            logger.info("Embedded chunks not available, loading from file system")

            # Search for chunks file
            possible_paths = [
                Path("chunks_data.json.gz"),
                Path("chunks_data.json"),
                Path("api/chunks_data.json.gz"),
                Path("api/chunks_data.json"),
                Path("../chunks_data.json.gz"),
                Path("../chunks_data.json"),
                Path("output/chromadb_data/chunks_data.json"),
            ]

            knowledge_file = None
            for path in possible_paths:
                if path.exists():
                    knowledge_file = path
                    logger.info(f"Found chunks file at: {path}")
                    break

            if not knowledge_file:
                raise FileNotFoundError("Could not find chunks_data.json or chunks_data.json.gz")

            # Load data
            if str(knowledge_file).endswith('.gz'):
                with gzip.open(knowledge_file, 'rt', encoding='utf-8') as f:
                    data = json.load(f)
            else:
                with open(knowledge_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)

        chunks = data.get('chunks', [])

        # Organize by namespace (for multi-tenancy support)
        # For now, all chunks go to default namespace
        _knowledge_base['management-knowledge'] = chunks
        _knowledge_loaded = True

        logger.info(f"✅ Knowledge base loaded: {len(chunks)} chunks in memory")
        return _knowledge_base

    except Exception as e:
        logger.error(f"❌ Failed to load knowledge base: {e}")
        raise


@app.on_event("startup")
async def startup_event():
    """Load knowledge base once at startup"""
    logger.info("🚀 Starting Knowledge Service v4.0")
    try:
        load_chunks_once()
        logger.info("✅ Knowledge Service ready")
    except Exception as e:
        logger.error(f"❌ Startup failed: {e}")
        # Don't crash, but log the error


@app.get("/api/health")
async def health_check():
    """Health check endpoint"""
    try:
        namespaces_info = {}
        for namespace, chunks in _knowledge_base.items():
            namespaces_info[namespace] = {
                "chunk_count": len(chunks),
                "total_words": sum(c.get('word_count', 0) for c in chunks)
            }

        return {
            "status": "healthy" if _knowledge_loaded else "loading",
            "service": "Knowledge Service v4.0",
            "version": "4.0.0",
            "architecture": "Efficient - loads once, searches fast",
            "knowledge_loaded": _knowledge_loaded,
            "namespaces": namespaces_info,
            "improvements": [
                "✅ Loads chunks ONCE at startup (not on every request)",
                "✅ Keeps all data in memory for instant access",
                "✅ No fake embeddings - pure semantic keyword search",
                "✅ Multi-tenant namespace support",
                "✅ Fast response times"
            ]
        }
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return {
            "status": "unhealthy",
            "error": str(e),
            "knowledge_loaded": _knowledge_loaded
        }


def semantic_search(query: str, chunks: List[Dict], top_k: int = 5) -> List[SearchResult]:
    """
    Fast semantic keyword search through in-memory chunks.
    No unpacking, no decompression - data already in memory!
    """
    query_lower = query.lower()
    query_words = query_lower.split()

    # Score each chunk
    scored_chunks = []
    for chunk in chunks:
        content = chunk['content'].lower()
        source_file = chunk['metadata'].get('source_file', '').lower()
        framework = chunk['metadata'].get('framework', '').lower()

        score = 0

        # 1. Exact phrase matching (highest priority)
        if query_lower in content:
            score += 100

        # 2. Source file matching
        for word in query_words:
            if len(word) > 2:
                if word in source_file:
                    score += 50
                if word in framework:
                    score += 30

        # 3. Word frequency in content
        for word in query_words:
            if len(word) > 2:
                count = content.count(word)
                score += count * len(word) * 5

        # 4. Semantic category boosting
        semantic_categories = {
            'feedback': ['sbi', 'situation', 'behavior', 'impact', 'radical', 'candor'],
            'coaching': ['development', '1:1', 'growth', 'mentoring', 'guidance'],
            'delegation': ['authority', 'responsibility', 'accountability', 'decision'],
            'leadership': ['management', 'leading', 'influence', 'direction'],
            'communication': ['conversation', 'discussion', 'talking', 'speaking']
        }

        for category, keywords in semantic_categories.items():
            if category in query_lower:
                for keyword in keywords:
                    if keyword in content:
                        score += 20

        # 5. Framework-specific boosting
        if 'feedback' in query_lower:
            if all(term in content for term in ['situation', 'behavior', 'impact']):
                score += 100  # Found complete SBI framework

        if 'coaching' in query_lower:
            if any(term in content for term in ['development', 'growth', 'conversation']):
                score += 50

        if score > 0:
            scored_chunks.append((chunk, score))

    # Sort by score and return top_k
    scored_chunks.sort(key=lambda x: x[1], reverse=True)

    results = []
    for chunk, score in scored_chunks[:top_k]:
        results.append(SearchResult(
            id=chunk['id'],
            content=chunk['content'],
            metadata={
                'source_file': chunk['metadata'].get('source_file', 'Unknown'),
                'framework': chunk['metadata'].get('framework', 'Unknown'),
                'category': chunk['metadata'].get('category', 'General'),
                'section': chunk['metadata'].get('section', ''),
                'word_count': chunk.get('word_count', 0)
            },
            score=float(score) / 100.0
        ))

    return results


@app.post("/api/search", response_model=SearchResponse)
async def search_knowledge(request: SearchRequest):
    """
    Search the knowledge base - FAST because data is already in memory!
    No unpacking, no decompression on every request.
    """
    try:
        if not _knowledge_loaded:
            raise HTTPException(status_code=503, detail="Knowledge base not loaded yet")

        # Get chunks for this namespace
        chunks = _knowledge_base.get(request.namespace)
        if not chunks:
            raise HTTPException(
                status_code=404,
                detail=f"Namespace '{request.namespace}' not found. Available: {list(_knowledge_base.keys())}"
            )

        # Fast search through in-memory data
        results = semantic_search(request.query, chunks, request.top_k)

        logger.info(f"Search '{request.query}' in namespace '{request.namespace}': {len(results)} results")

        return SearchResponse(
            results=results,
            total_results=len(results),
            query=request.query,
            namespace=request.namespace
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Search failed: {e}")
        raise HTTPException(status_code=500, detail=f"Search failed: {e}")


@app.post("/api/ask")
async def ask_question(request: AskRequest):
    """
    Ask a question - returns context sources only.
    The platform adapter (Custom GPT, Slack, etc.) handles AI generation.
    This keeps the knowledge service simple and fast.
    """
    try:
        # Search for relevant sources
        search_request = SearchRequest(
            query=request.question,
            top_k=request.top_k,
            namespace=request.namespace
        )
        search_response = await search_knowledge(search_request)

        if not search_response.results:
            return {
                "answer": "I don't have specific information about this in the knowledge base.",
                "sources": [],
                "question": request.question,
                "namespace": request.namespace
            }

        # Return sources - let the platform adapter handle AI generation
        return {
            "sources": search_response.results,
            "question": request.question,
            "namespace": request.namespace,
            "note": "Platform adapter should use these sources to generate AI response"
        }

    except Exception as e:
        logger.error(f"Ask question failed: {e}")
        raise HTTPException(status_code=500, detail=f"Question processing failed: {e}")


# Root endpoint
@app.get("/")
async def root():
    return {
        "service": "Management Knowledge Service v4.0",
        "status": "running",
        "endpoints": {
            "health": "/api/health",
            "search": "POST /api/search",
            "ask": "POST /api/ask"
        }
    }


# For Vercel serverless
def handler(request, response):
    """Vercel serverless handler"""
    return app(request, response)

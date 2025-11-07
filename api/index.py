#!/usr/bin/env python3
"""
Knowledge Service API v5.0 - Real Vector Search
- Loads chunks ONCE at startup (not on every request)
- REAL vector similarity search with OpenAI embeddings
- Multi-tenant namespace support
- Hybrid search: Vector + Keyword fallback
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
import uvicorn

# Global clients and cache (loaded ONCE at startup)
_knowledge_base: Dict[str, List[Dict]] = {}
_knowledge_loaded = False
_pinecone_index = None
_openai_client = None

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
    Returns dict mapping namespace -> list of chunks.
    NO UNPACKING ON EVERY REQUEST!
    """
    global _knowledge_loaded

    if _knowledge_loaded:
        logger.info("Knowledge base already loaded in memory")
        return _knowledge_base

    try:
        # Try embedded base64 first (for Vercel)
        try:
            from api.embedded_chunks import CHUNKS_DATA_B64
            logger.info("Loading from embedded base64 data (ONCE at startup)")
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

            # Load data ONCE
            if str(knowledge_file).endswith('.gz'):
                with gzip.open(knowledge_file, 'rt', encoding='utf-8') as f:
                    data = json.load(f)
            else:
                with open(knowledge_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)

        chunks = data.get('chunks', [])

        # Load chunks into cache
        # Check if chunks have namespace info, otherwise use default
        namespace_chunks = {}
        for chunk in chunks:
            ns = chunk.get('namespace', 'management-knowledge')  # Default namespace
            if ns not in namespace_chunks:
                namespace_chunks[ns] = []
            namespace_chunks[ns].append(chunk)

        # Store all namespaces in cache
        _knowledge_base.update(namespace_chunks)
        _knowledge_loaded = True

        total_chunks = sum(len(chunks) for chunks in namespace_chunks.values())
        logger.info(f"✅ Knowledge base loaded ONCE at startup: {total_chunks} chunks across {len(namespace_chunks)} namespace(s)")
        logger.info(f"   Namespaces: {list(namespace_chunks.keys())}")
        return _knowledge_base

    except Exception as e:
        logger.error(f"❌ Failed to load knowledge base: {e}")
        raise

def get_pinecone_index():
    """Initialize Pinecone client and return index"""
    global _pinecone_index
    if _pinecone_index is None:
        try:
            from pinecone import Pinecone
            api_key = os.getenv('PINECONE_API_KEY')
            if not api_key:
                logger.warning("PINECONE_API_KEY not found - vector search disabled")
                return None

            index_name = os.getenv('PINECONE_INDEX_NAME', 'management-knowledge-v2')
            pc = Pinecone(api_key=api_key)
            _pinecone_index = pc.Index(index_name)
            logger.info(f"✅ Pinecone connected: {index_name}")
        except Exception as e:
            logger.error(f"Failed to initialize Pinecone: {e}")
            return None
    return _pinecone_index

def get_openai_client():
    """Initialize OpenAI client"""
    global _openai_client
    if _openai_client is None:
        try:
            from openai import OpenAI
            api_key = os.getenv('OPENAI_API_KEY')
            if api_key:
                _openai_client = OpenAI(api_key=api_key)
                logger.info("✅ OpenAI client initialized")
            else:
                logger.warning("OPENAI_API_KEY not found - using keyword search only")
        except Exception as e:
            logger.error(f"Failed to initialize OpenAI client: {e}")
    return _openai_client

def create_query_embedding(query: str) -> Optional[List[float]]:
    """Create real embedding for search query using OpenAI"""
    try:
        client = get_openai_client()
        if not client:
            return None

        response = client.embeddings.create(
            model="text-embedding-3-small",  # 1536 dimensions
            input=query
        )

        return response.data[0].embedding
    except Exception as e:
        logger.error(f"Failed to create query embedding: {e}")
        return None


@app.on_event("startup")
async def startup_event():
    """Load knowledge base and initialize clients once at startup"""
    logger.info("🚀 Starting Knowledge Service v5.0 - Real Vector Search")
    try:
        # Load chunks into memory
        load_chunks_once()
        logger.info("✅ Knowledge base loaded in memory")

        # Initialize Pinecone
        get_pinecone_index()

        # Initialize OpenAI
        get_openai_client()

        logger.info("✅ Knowledge Service ready with REAL vector search")
    except Exception as e:
        logger.error(f"❌ Startup failed: {e}")
        # Don't crash, but log the error


@app.get("/api/health")
async def health_check():
    """Health check endpoint"""
    try:
        # Get namespace stats from in-memory knowledge base
        namespaces_info = {}
        for namespace, chunks in _knowledge_base.items():
            namespaces_info[namespace] = {
                "chunk_count": len(chunks),
                "total_words": sum(c.get('word_count', 0) for c in chunks)
            }

        # Check services
        pinecone_available = _pinecone_index is not None
        openai_available = _openai_client is not None

        # Get Pinecone stats if available
        pinecone_stats = {}
        if pinecone_available:
            try:
                stats = _pinecone_index.describe_index_stats()
                pinecone_stats = {
                    "total_vectors": stats.total_vector_count,
                    "namespaces": {
                        ns: stats.namespaces.get(ns, {}).get('vector_count', 0)
                        for ns in stats.namespaces.keys()
                    }
                }
            except Exception as e:
                pinecone_stats = {"error": str(e)}

        return {
            "status": "healthy" if _knowledge_loaded else "loading",
            "service": "Management Knowledge Service v5.0",
            "version": "5.0.0",
            "architecture": "REAL Vector Search with OpenAI embeddings",
            "knowledge_loaded": _knowledge_loaded,
            "namespaces": namespaces_info,
            "search_capabilities": {
                "vector_search": pinecone_available and openai_available,
                "keyword_search": True,
                "hybrid_search": True
            },
            "services": {
                "pinecone": pinecone_available,
                "openai": openai_available
            },
            "pinecone_stats": pinecone_stats,
            "improvements": [
                "✅ REAL vector embeddings (OpenAI text-embedding-3-small)",
                "✅ True semantic similarity search via Pinecone",
                "✅ Hybrid search: Vector primary, keyword fallback",
                "✅ Loads chunks ONCE at startup",
                "✅ Multi-tenant namespace support"
            ]
        }
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return {
            "status": "unhealthy",
            "error": str(e),
            "knowledge_loaded": _knowledge_loaded
        }

def vector_search(query: str, namespace: str, top_k: int = 5) -> Optional[List[SearchResult]]:
    """
    Real vector similarity search using Pinecone + OpenAI embeddings
    Returns None if vector search unavailable (falls back to keyword search)
    """
    try:
        # Check if vector search available
        index = get_pinecone_index()
        if not index:
            logger.info("Pinecone not available, using keyword fallback")
            return None

        # Create real embedding for query
        query_embedding = create_query_embedding(query)
        if not query_embedding:
            logger.info("Could not create query embedding, using keyword fallback")
            return None

        # Search Pinecone with REAL vector similarity
        search_results = index.query(
            vector=query_embedding,
            top_k=top_k,
            namespace=namespace,
            include_metadata=True
        )

        if not search_results.matches:
            logger.info(f"No vector results found for: {query}")
            return None

        # Get full content from in-memory cache
        chunks_map = {c['id']: c for c in _knowledge_base.get(namespace, [])}

        results = []
        for match in search_results.matches:
            try:
                # Get full content from cache (best option)
                chunk = chunks_map.get(match.id)
                if chunk:
                    results.append(SearchResult(
                        id=match.id,
                        content=chunk['content'],
                        metadata={
                            'source_file': chunk['metadata'].get('source_file', 'Unknown'),
                            'framework': chunk['metadata'].get('framework', 'Unknown'),
                            'category': chunk['metadata'].get('category', 'General'),
                            'section': chunk['metadata'].get('section', ''),
                            'word_count': chunk.get('word_count', 0)
                        },
                        score=float(match.score)
                    ))
                else:
                    # Fallback to Pinecone metadata (safe handling for None/missing)
                    # Guard against None, missing attribute, or empty metadata
                    try:
                        metadata = getattr(match, 'metadata', None) or {}
                    except AttributeError:
                        metadata = {}

                    if not metadata:
                        logger.warning(f"Chunk {match.id} in namespace {namespace} has no metadata and not in cache - skipping")
                        continue  # Skip this result entirely if no content available

                    # Try multiple fields for content (new format, old format, fallback)
                    content = metadata.get('content') or metadata.get('content_preview') or metadata.get('text')

                    if not content:
                        logger.warning(f"Chunk {match.id} has metadata but no content field - skipping")
                        continue  # Skip if metadata exists but has no content

                    is_truncated = metadata.get('content_truncated', False)
                    if is_truncated:
                        logger.info(f"Chunk {match.id} using truncated content from Pinecone metadata")

                    results.append(SearchResult(
                        id=match.id,
                        content=content,
                        metadata={
                            'source_file': metadata.get('source_file', 'Unknown'),
                            'framework': metadata.get('framework', 'Unknown'),
                            'category': metadata.get('category', 'General'),
                            'section': metadata.get('section', ''),
                            'word_count': metadata.get('word_count', 0),
                            'content_truncated': is_truncated
                        },
                        score=float(match.score)
                    ))
            except Exception as e:
                logger.error(f"Error processing vector match {match.id}: {e}")
                continue  # Skip problematic results, don't crash entire search

        logger.info(f"✅ Vector search found {len(results)} results (scores: {[r.score for r in results[:3]]})")
        return results

    except Exception as e:
        logger.error(f"Vector search failed: {e}")
        return None


def keyword_search(query: str, chunks: List[Dict], top_k: int = 5) -> List[SearchResult]:
    """
    Fast semantic keyword search through in-memory chunks.
    NO FILE LOADING - data already in memory from startup!
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
    Hybrid Search: Real vector similarity (primary) + keyword fallback

    1. Try vector search with real OpenAI embeddings + Pinecone
    2. Fall back to keyword search if vector unavailable OR namespace not cached

    Multi-tenant: Works even if namespace not in local cache (uses Pinecone directly)
    """
    try:
        # Try REAL vector search first (works for any namespace in Pinecone)
        results = vector_search(request.query, request.namespace, request.top_k)
        search_method = "vector"

        # Fall back to keyword search if vector unavailable
        if results is None:
            # Check if we have this namespace in local cache for keyword search
            chunks = _knowledge_base.get(request.namespace)
            if chunks:
                logger.info(f"Vector search unavailable, using keyword search for: {request.query}")
                results = keyword_search(request.query, chunks, request.top_k)
                search_method = "keyword"
            else:
                # Neither vector nor keyword available for this namespace
                raise HTTPException(
                    status_code=404,
                    detail=f"Namespace '{request.namespace}' not found in cache and vector search unavailable. Available cached namespaces: {list(_knowledge_base.keys())}"
                )

        logger.info(f"Search '{request.query}' ({search_method}): {len(results)} results")

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
        "architecture": "Efficient - loads once at startup",
        "endpoints": {
            "health": "/api/health",
            "search": "POST /api/search",
            "ask": "POST /api/ask"
        }
    }


# Main entry point for local development
if __name__ == "__main__":
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)

# For Vercel: Export the app directly (Vercel auto-detects FastAPI apps)
# No handler function needed - Vercel uses the 'app' object automatically
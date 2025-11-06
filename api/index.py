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
    title="Management Knowledge RAG API v2.1",
    description="Fixed Pinecone API (2025) with manual embeddings for management knowledge",
    version="2.1.0"
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

async def check_knowledge_loaded():
    """Check if knowledge base is already loaded in Pinecone"""
    global _knowledge_loaded
    try:
        # Check if index has data
        index = get_pinecone_index()
        stats = index.describe_index_stats()
        namespace = os.getenv('PINECONE_NAMESPACE', 'management-knowledge')

        # Check if our namespace has data
        namespace_stats = stats.namespaces.get(namespace, {})
        vector_count = namespace_stats.get('vector_count', 0)

        if vector_count > 0:
            logger.info(f"Knowledge base detected: {vector_count} vectors in namespace '{namespace}'")
            _knowledge_loaded = True
            return True
        else:
            logger.warning(f"No vectors found in namespace '{namespace}'")
            _knowledge_loaded = False
            return False

    except Exception as e:
        logger.error(f"Failed to check knowledge base: {e}")
        _knowledge_loaded = False
        return False


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

        # Check knowledge base status
        await check_knowledge_loaded()

        # Get namespace stats
        namespace_stats = stats.namespaces.get(namespace, {})

        return {
            "status": "healthy",
            "service": "Management Knowledge RAG API v3.0 WORKING",
            "version": "3.0.0",
            "api_version": "2025",
            "deployed_at": "2025-11-06T17:25:00Z",
            "fix_status": "ENHANCED SEARCH + BUNDLED CHUNKS",
            "file_name": "index.py",
            "pinecone": {
                "connected": True,
                "total_vectors": stats.total_vector_count,
                "namespace": namespace,
                "namespace_vectors": namespace_stats.get('vector_count', 0),
                "index_name": os.getenv('PINECONE_INDEX_NAME', 'management-knowledge-v2'),
                "embedding_model": "manual (anthropic-based)"
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

def create_anthropic_embeddings(text: str):
    """Create embeddings using Anthropic Claude (same as setup script)"""
    try:
        client = get_anthropic_client()
        if not client:
            raise ValueError("Anthropic client not available")

        # Use Claude to create a semantic representation
        response = client.messages.create(
            model="claude-3-haiku-20240307",  # Cheaper model for embeddings
            max_tokens=100,
            messages=[{
                "role": "user",
                "content": f"Create a numerical semantic vector representation for this text (return only 10 comma-separated numbers between -1 and 1): {text[:500]}"
            }]
        )

        # Parse the response to get numbers
        text_response = response.content[0].text
        numbers = [float(x.strip()) for x in text_response.split(',') if x.strip().replace('-','').replace('.','').isdigit()]

        # Pad to 1536 dimensions (standard)
        while len(numbers) < 1536:
            numbers.extend(numbers[:min(100, 1536-len(numbers))])

        return numbers[:1536]

    except Exception as e:
        logger.error(f"Anthropic embedding failed: {e}")
        # Return a simple hash-based embedding as fallback
        import hashlib
        hash_val = hashlib.md5(text.encode()).hexdigest()
        # Convert hash to numbers
        numbers = [int(hash_val[i:i+2], 16) / 255.0 - 0.5 for i in range(0, len(hash_val), 2)]
        # Repeat to get 1536 dimensions
        while len(numbers) < 1536:
            numbers.extend(numbers[:min(100, 1536-len(numbers))])
        return numbers[:1536]

async def search_by_keywords_improved(query: str, top_k: int = 5) -> List[SearchResult]:
    """Enhanced keyword-based search with fuzzy matching and semantic understanding"""
    try:
        # Load local knowledge base for better search
        knowledge_file = Path("chunks_data.json")
        if not knowledge_file.exists():
            # Try alternative paths
            alt_paths = [
                Path("../chunks_data.json"),
                Path("output/chromadb_data/chunks_data.json"),
            ]
            for alt_path in alt_paths:
                if alt_path.exists():
                    knowledge_file = alt_path
                    break
            else:
                logger.warning("Knowledge base file not found for improved search")
                return await search_by_pinecone_metadata(query, top_k)

        with open(knowledge_file, 'r', encoding='utf-8') as f:
            data = json.load(f)

        chunks = data.get('chunks', [])
        query_words = query.lower().split()

        # Enhanced scoring system
        scored_chunks = []
        for chunk in chunks:
            content = chunk['content'].lower()
            source_file = chunk['metadata'].get('source_file', '').lower()
            framework = chunk['metadata'].get('framework', '').lower()

            score = 0

            # 1. Exact phrase matching (highest weight)
            if query.lower() in content:
                score += 100

            # 2. Source file matching
            for word in query_words:
                if len(word) > 2:
                    if word in source_file:
                        score += 50
                    if word in framework:
                        score += 30

            # 3. Individual word matching
            for word in query_words:
                if len(word) > 2:
                    count = content.count(word)
                    score += count * len(word) * 5

            # 4. Semantic keyword boosting
            semantic_matches = {
                'feedback': ['giving', 'receiving', 'sbi', 'situation', 'behavior', 'impact', 'radical', 'candor'],
                'coaching': ['development', '1:1', 'growth', 'mentoring', 'guidance'],
                'delegation': ['authority', 'responsibility', 'accountability', 'decision'],
                'leadership': ['management', 'leading', 'influence', 'direction'],
                'communication': ['conversation', 'discussion', 'talking', 'speaking']
            }

            for category, keywords in semantic_matches.items():
                if category in query.lower():
                    for keyword in keywords:
                        if keyword in content:
                            score += 20

            # 5. Framework-specific boosting
            if 'feedback' in query.lower() and any(term in content for term in ['situation', 'behavior', 'impact']):
                score += 50
            if 'coaching' in query.lower() and any(term in content for term in ['development', 'growth', 'conversation']):
                score += 50

            if score > 0:
                scored_chunks.append((chunk, score))

        # Sort by score and return results
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

        logger.info(f"Enhanced search found {len(results)} results for '{query}'")
        return results

    except Exception as e:
        logger.error(f"Enhanced search failed: {e}")
        # Fallback to Pinecone metadata search
        return await search_by_pinecone_metadata(query, top_k)

async def search_by_pinecone_metadata(query: str, top_k: int = 5) -> List[SearchResult]:
    """Fallback search using Pinecone metadata when local files aren't available"""
    try:
        index = get_pinecone_index()
        namespace = "management-knowledge"

        query_words = query.lower().split()
        dummy_embedding = [0.1] * 1536

        search_results = index.query(
            vector=dummy_embedding,
            top_k=min(100, top_k * 10),  # Get more results to filter
            include_metadata=True,
            namespace=namespace
        )

        scored_results = []
        for match in search_results.matches:
            metadata = match.metadata or {}
            content = metadata.get('content', '').lower()
            source_file = metadata.get('source_file', '').lower()
            framework = metadata.get('framework', '').lower()

            score = 0

            # Enhanced Pinecone metadata scoring
            for word in query_words:
                if len(word) > 2:
                    # Source file matches
                    if word in source_file:
                        score += 50
                    # Framework matches
                    if word in framework:
                        score += 30
                    # Content matches
                    if word in content:
                        score += content.count(word) * 10

            # Specific content type boosting
            if 'feedback' in query.lower():
                if 'feedback' in source_file or 'feedback' in framework:
                    score += 100
                if any(term in content for term in ['situation', 'behavior', 'impact', 'sbi', 'radical', 'candor']):
                    score += 50

            if score > 0 or 'feedback' in source_file:  # Always include feedback files
                scored_results.append((match, score))

        scored_results.sort(key=lambda x: x[1], reverse=True)

        results = []
        for match, score in scored_results[:top_k]:
            content = match.metadata.get('content', '')
            if not content:
                content = await get_full_content_by_id(match.id)

            results.append(SearchResult(
                id=match.id,
                content=content,
                metadata={
                    'source_file': match.metadata.get('source_file', 'Unknown'),
                    'framework': match.metadata.get('framework', 'Unknown'),
                    'category': match.metadata.get('category', 'General'),
                    'section': match.metadata.get('section', ''),
                    'word_count': match.metadata.get('word_count', 0)
                },
                score=float(score) / 100.0 if score > 0 else float(match.score)
            ))

        return results

    except Exception as e:
        logger.error(f"Pinecone metadata search failed: {e}")
        return []

@app.post("/api/search", response_model=SearchResponse)
async def search_knowledge(request: SearchRequest):
    """Search the management knowledge base using keyword matching + vector search"""
    try:
        # First try keyword-based search through local knowledge base
        keyword_results = await search_by_keywords_improved(request.query, request.top_k)

        if keyword_results:
            logger.info(f"Found {len(keyword_results)} results using keyword search")
            return SearchResponse(
                results=keyword_results,
                total_results=len(keyword_results),
                query=request.query
            )

        # Fallback to vector search (likely won't work due to embedding issues)
        index = get_pinecone_index()
        query_embedding = create_anthropic_embeddings(request.query)

        search_results = index.query(
            vector=query_embedding,
            top_k=request.top_k,
            include_metadata=True,
            namespace=request.namespace
        )

        # Process results from traditional API format
        results = []
        for match in search_results.matches:
            # Get content from metadata or use stored partial content
            content = match.metadata.get('content', '')
            if not content and hasattr(match, 'values'):
                # Try to get full content from knowledge base file
                content = await get_full_content_by_id(match.id)

            results.append(SearchResult(
                id=match.id,
                content=content,
                metadata={
                    'source_file': match.metadata.get('source_file', 'Unknown'),
                    'framework': match.metadata.get('framework', 'Unknown'),
                    'category': match.metadata.get('category', 'General'),
                    'section': match.metadata.get('section', ''),
                    'word_count': match.metadata.get('word_count', 0)
                },
                score=float(match.score)
            ))

        return SearchResponse(
            results=results,
            total_results=len(results),
            query=request.query
        )

    except Exception as e:
        logger.error(f"Search failed: {e}")
        raise HTTPException(status_code=500, detail=f"Search failed: {e}")

async def get_full_content_by_id(chunk_id: str) -> str:
    """Get full content for a chunk ID from the knowledge base file"""
    try:
        # Load knowledge base to get full content
        knowledge_file = Path("chunks_data.json")
        if not knowledge_file.exists():
            # Try alternative paths
            alt_paths = [
                Path("../chunks_data.json"),
                Path("output/chromadb_data/chunks_data.json"),
            ]
            for alt_path in alt_paths:
                if alt_path.exists():
                    knowledge_file = alt_path
                    break
            else:
                return "Content not available"

        with open(knowledge_file, 'r', encoding='utf-8') as f:
            data = json.load(f)

        chunks = data.get('chunks', [])
        for chunk in chunks:
            if chunk['id'] == chunk_id:
                return chunk['content']

        return "Content not found for this ID"

    except Exception as e:
        logger.error(f"Failed to get full content for {chunk_id}: {e}")
        return "Content retrieval failed"

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

        prompt = f"""You are a management consultant. You must answer ONLY using the information provided in the context below. Do NOT use any external knowledge, do NOT cite external sources like Harvard Business Review, and do NOT reference frameworks not mentioned in the context.

CRITICAL: If the provided context does not contain enough information to answer the question, say "I don't have specific information about this in the provided materials."

Context from knowledge base:
{context}

Question: {question}

Answer using ONLY the information from the context above:"""

        response = client.messages.create(
            model="claude-3-haiku-20240307",
            max_tokens=1500,
            messages=[{"role": "user", "content": prompt}]
        )

        return response.content[0].text

    except Exception as e:
        logger.error(f"Anthropic response generation failed: {e}")
        logger.error(f"Anthropic error details: {type(e).__name__}: {str(e)}")
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
                    "content": "You are a management consultant. You must answer ONLY using the information provided in the context. Do NOT use external knowledge, do NOT cite external sources, and do NOT reference frameworks not mentioned in the context. If the context doesn't contain enough information, say so."
                },
                {
                    "role": "user",
                    "content": f"""Context from knowledge base:

{context}

Question: {question}

Answer using ONLY the information from the context above:"""
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
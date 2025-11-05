#!/usr/bin/env python3
"""
Pinecone-based RAG API for Management Knowledge Base
Uses full-quality knowledge base with rich metadata
"""
import json
import os
import logging
from typing import Dict, List, Optional, Any
from pathlib import Path
import hashlib

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
    filter: Optional[Dict[str, Any]] = None

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

class AskResponse(BaseModel):
    answer: str
    sources: List[SearchResult]
    ai_provider: str
    question: str

# Initialize FastAPI app
app = FastAPI(
    title="Management Knowledge RAG API",
    description="Pinecone-powered semantic search and AI responses for management frameworks",
    version="1.0.0"
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
    """Initialize Pinecone client (singleton)"""
    global _pinecone_client
    if _pinecone_client is None:
        try:
            from pinecone import Pinecone
            api_key = os.getenv('PINECONE_API_KEY')
            if not api_key:
                raise ValueError("PINECONE_API_KEY environment variable not set")
            _pinecone_client = Pinecone(api_key=api_key)
            logger.info("Pinecone client initialized")
        except Exception as e:
            logger.error(f"Failed to initialize Pinecone client: {e}")
            raise HTTPException(status_code=500, detail=f"Pinecone initialization failed: {e}")
    return _pinecone_client

def get_pinecone_index():
    """Get Pinecone index (singleton)"""
    global _pinecone_index
    if _pinecone_index is None:
        try:
            client = get_pinecone_client()
            index_name = os.getenv('PINECONE_INDEX_NAME', 'management-knowledge')
            _pinecone_index = client.Index(index_name)
            logger.info(f"Connected to Pinecone index: {index_name}")
        except Exception as e:
            logger.error(f"Failed to connect to Pinecone index: {e}")
            raise HTTPException(status_code=500, detail=f"Pinecone index connection failed: {e}")
    return _pinecone_index

def get_anthropic_client():
    """Initialize Anthropic client (singleton)"""
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
    """Initialize OpenAI client (singleton)"""
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

def create_embeddings(text: str) -> List[float]:
    """Create embeddings using OpenAI's text-embedding-ada-002"""
    try:
        openai_client = get_openai_client()
        if not openai_client:
            raise HTTPException(status_code=500, detail="OpenAI client not available for embeddings")

        response = openai_client.embeddings.create(
            model="text-embedding-ada-002",
            input=text
        )
        return response.data[0].embedding
    except Exception as e:
        logger.error(f"Failed to create embeddings: {e}")
        raise HTTPException(status_code=500, detail=f"Embedding creation failed: {e}")

async def ensure_knowledge_loaded():
    """Ensure knowledge base is loaded into Pinecone"""
    global _knowledge_loaded
    if _knowledge_loaded:
        return

    try:
        # Check if index has data
        index = get_pinecone_index()
        stats = index.describe_index_stats()

        if stats.total_vector_count > 0:
            logger.info(f"Knowledge base already loaded: {stats.total_vector_count} vectors")
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

        logger.info(f"Processing {len(chunks)} chunks for Pinecone upload")

        # Process chunks in batches
        batch_size = 100
        total_uploaded = 0

        for i in range(0, len(chunks), batch_size):
            batch = chunks[i:i + batch_size]
            vectors = []

            for chunk in batch:
                # Create embedding for the content
                embedding = create_embeddings(chunk['content'])

                # Prepare metadata (Pinecone has metadata size limits)
                metadata = {
                    'source_file': chunk['metadata'].get('source_file', 'Unknown'),
                    'framework': chunk['metadata'].get('framework', 'Unknown'),
                    'category': chunk['metadata'].get('category', 'General'),
                    'section': chunk['metadata'].get('section', ''),
                    'chunk_type': chunk['metadata'].get('chunk_type', 'unknown'),
                    'word_count': chunk.get('word_count', 0),
                    'language': chunk['metadata'].get('language', 'unknown'),
                    'content_preview': chunk['content'][:200]  # First 200 chars for preview
                }

                vectors.append({
                    'id': chunk['id'],
                    'values': embedding,
                    'metadata': metadata
                })

            # Upload batch to Pinecone
            index.upsert(vectors=vectors)
            total_uploaded += len(vectors)
            logger.info(f"Uploaded batch {i//batch_size + 1}: {total_uploaded}/{len(chunks)} chunks")

        logger.info(f"Successfully uploaded {total_uploaded} chunks to Pinecone")
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

        # Check AI providers
        anthropic_available = get_anthropic_client() is not None
        openai_available = get_openai_client() is not None

        return {
            "status": "healthy",
            "service": "Management Knowledge RAG API",
            "version": "1.0.0",
            "pinecone": {
                "connected": True,
                "total_vectors": stats.total_vector_count,
                "index_name": os.getenv('PINECONE_INDEX_NAME', 'management-knowledge')
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
            "error": str(e)
        }

@app.post("/api/search", response_model=SearchResponse)
async def search_knowledge(request: SearchRequest):
    """Search the management knowledge base"""
    try:
        await ensure_knowledge_loaded()

        # Create embedding for the query
        query_embedding = create_embeddings(request.query)

        # Search in Pinecone
        index = get_pinecone_index()
        search_results = index.query(
            vector=query_embedding,
            top_k=request.top_k,
            include_metadata=True,
            filter=request.filter
        )

        # Process results
        results = []
        for match in search_results.matches:
            # Get full content from knowledge base
            content = await get_full_content(match.id)

            results.append(SearchResult(
                id=match.id,
                content=content,
                metadata=match.metadata,
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

async def get_full_content(chunk_id: str) -> str:
    """Get full content for a chunk ID from the knowledge base"""
    try:
        # Load knowledge base to get full content
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

        with open(knowledge_file, 'r', encoding='utf-8') as f:
            data = json.load(f)

        # Find the chunk by ID
        for chunk in data.get('chunks', []):
            if chunk['id'] == chunk_id:
                return chunk['content']

        return "Content not found"
    except Exception as e:
        logger.error(f"Failed to get full content for {chunk_id}: {e}")
        return "Error retrieving content"

@app.post("/api/ask", response_model=AskResponse)
async def ask_question(request: AskRequest):
    """Ask a question and get an AI-powered response with sources"""
    try:
        # First, search for relevant context
        search_request = SearchRequest(
            query=request.question,
            top_k=request.top_k
        )
        search_response = await search_knowledge(search_request)

        if not search_response.results:
            raise HTTPException(status_code=404, detail="No relevant knowledge found for this question")

        # Prepare context from search results
        context_parts = []
        for i, result in enumerate(search_response.results, 1):
            context_parts.append(f"Source {i} ({result.metadata.get('source_file', 'Unknown')}):\n{result.content}\n")

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
#!/usr/bin/env python3
"""
Setup script for Pinecone knowledge base
Creates Pinecone index and uploads full-quality knowledge base
"""
import json
import os
import logging
from pathlib import Path
from typing import List, Dict, Any

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def load_environment():
    """Load environment variables from .env file if it exists"""
    env_file = Path('.env')
    if env_file.exists():
        with open(env_file) as f:
            for line in f:
                if line.strip() and not line.startswith('#'):
                    key, value = line.strip().split('=', 1)
                    os.environ[key] = value

def create_pinecone_index():
    """Create Pinecone index for the knowledge base"""
    try:
        from pinecone import Pinecone, ServerlessSpec

        # Load environment
        load_environment()

        api_key = os.getenv('PINECONE_API_KEY')
        if not api_key:
            raise ValueError("PINECONE_API_KEY not found in environment variables")

        # Initialize Pinecone
        pc = Pinecone(api_key=api_key)

        index_name = "management-knowledge"
        dimension = 1536  # OpenAI text-embedding-ada-002 dimension

        # Check if index already exists
        existing_indexes = pc.list_indexes().names()

        if index_name in existing_indexes:
            logger.info(f"Index '{index_name}' already exists")
            return pc.Index(index_name)

        # Create new index
        logger.info(f"Creating Pinecone index: {index_name}")
        pc.create_index(
            name=index_name,
            dimension=dimension,
            metric="cosine",
            spec=ServerlessSpec(
                cloud="aws",
                region="us-east-1"
            )
        )

        logger.info(f"Successfully created index: {index_name}")
        return pc.Index(index_name)

    except Exception as e:
        logger.error(f"Failed to create Pinecone index: {e}")
        raise

def upload_knowledge_base():
    """Upload the full knowledge base to Pinecone"""
    try:
        # Load environment
        load_environment()

        # Import OpenAI for embeddings
        import openai
        openai_api_key = os.getenv('OPENAI_API_KEY')
        if not openai_api_key:
            raise ValueError("OPENAI_API_KEY not found in environment variables")

        openai_client = openai.OpenAI(api_key=openai_api_key)

        # Create/get Pinecone index
        index = create_pinecone_index()

        # Load knowledge base
        knowledge_file = Path("output/chromadb_data/chunks_data.json")
        if not knowledge_file.exists():
            raise FileNotFoundError(f"Knowledge base file not found: {knowledge_file}")

        logger.info(f"Loading knowledge base from: {knowledge_file}")
        with open(knowledge_file, 'r', encoding='utf-8') as f:
            data = json.load(f)

        chunks = data.get('chunks', [])
        if not chunks:
            raise ValueError("No chunks found in knowledge base")

        logger.info(f"Processing {len(chunks)} chunks for upload")

        # Check if already uploaded
        stats = index.describe_index_stats()
        if stats.total_vector_count >= len(chunks):
            logger.info(f"Knowledge base already uploaded: {stats.total_vector_count} vectors")
            return

        # Process chunks in batches
        batch_size = 100
        total_uploaded = 0

        for i in range(0, len(chunks), batch_size):
            batch = chunks[i:i + batch_size]
            vectors = []

            logger.info(f"Processing batch {i//batch_size + 1}/{(len(chunks) + batch_size - 1)//batch_size}")

            for chunk in batch:
                try:
                    # Create embedding
                    response = openai_client.embeddings.create(
                        model="text-embedding-ada-002",
                        input=chunk['content']
                    )
                    embedding = response.data[0].embedding

                    # Prepare metadata (Pinecone has size limits)
                    metadata = {
                        'source_file': chunk['metadata'].get('source_file', 'Unknown')[:50],
                        'framework': chunk['metadata'].get('framework', 'Unknown')[:50],
                        'category': chunk['metadata'].get('category', 'General')[:50],
                        'section': chunk['metadata'].get('section', '')[:50],
                        'chunk_type': chunk['metadata'].get('chunk_type', 'unknown')[:20],
                        'word_count': int(chunk.get('word_count', 0)),
                        'language': chunk['metadata'].get('language', 'unknown')[:10],
                        'content_preview': chunk['content'][:200]
                    }

                    vectors.append({
                        'id': chunk['id'],
                        'values': embedding,
                        'metadata': metadata
                    })

                except Exception as e:
                    logger.error(f"Failed to process chunk {chunk['id']}: {e}")
                    continue

            if vectors:
                # Upload batch
                index.upsert(vectors=vectors)
                total_uploaded += len(vectors)
                logger.info(f"Uploaded {len(vectors)} vectors. Total: {total_uploaded}/{len(chunks)}")

        logger.info(f"Successfully uploaded {total_uploaded} chunks to Pinecone")

        # Verify upload
        final_stats = index.describe_index_stats()
        logger.info(f"Final index stats: {final_stats.total_vector_count} vectors")

    except Exception as e:
        logger.error(f"Failed to upload knowledge base: {e}")
        raise

def main():
    """Main setup function"""
    try:
        logger.info("Starting Pinecone knowledge base setup...")

        # Check required environment variables
        required_vars = ['PINECONE_API_KEY', 'OPENAI_API_KEY']
        missing_vars = [var for var in required_vars if not os.getenv(var)]

        if missing_vars:
            logger.error(f"Missing required environment variables: {missing_vars}")
            logger.info("Please set these variables in your .env file:")
            for var in missing_vars:
                logger.info(f"  {var}=your_api_key_here")
            return

        # Upload knowledge base
        upload_knowledge_base()

        logger.info("Pinecone setup completed successfully!")
        logger.info("Your RAG API is ready to use with the full knowledge base.")

    except Exception as e:
        logger.error(f"Setup failed: {e}")
        raise

if __name__ == "__main__":
    main()
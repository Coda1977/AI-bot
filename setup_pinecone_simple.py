#!/usr/bin/env python3
"""
Simple Pinecone setup without CLI requirement
Creates index using SDK and uploads knowledge base
"""
import json
import os
import logging
import time
from pathlib import Path

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def load_environment():
    """Load environment variables from .env file"""
    env_file = Path('.env')
    if env_file.exists():
        with open(env_file) as f:
            for line in f:
                if line.strip() and not line.startswith('#') and '=' in line:
                    key, value = line.strip().split('=', 1)
                    os.environ[key] = value
        logger.info("Environment variables loaded from .env file")

def setup_pinecone_index():
    """Setup Pinecone index using SDK approach"""
    try:
        from pinecone import Pinecone, ServerlessSpec

        # Load environment
        load_environment()

        api_key = os.getenv('PINECONE_API_KEY')
        if not api_key:
            logger.error("❌ PINECONE_API_KEY not found!")
            logger.info("Please edit your .env file and add:")
            logger.info("PINECONE_API_KEY=your_actual_pinecone_api_key")
            return False

        # Initialize Pinecone
        pc = Pinecone(api_key=api_key)
        logger.info("✅ Pinecone client initialized")

        # Index configuration
        index_name = os.getenv('PINECONE_INDEX_NAME', 'management-knowledge-v2')
        dimension = 1536  # Standard embedding dimension

        # Check if index exists
        existing_indexes = pc.list_indexes().names()

        if index_name in existing_indexes:
            logger.info(f"✅ Index '{index_name}' already exists")
            index = pc.Index(index_name)
        else:
            # Create index using SDK (fallback approach)
            logger.info(f"🔨 Creating index '{index_name}' using SDK...")
            pc.create_index(
                name=index_name,
                dimension=dimension,
                metric="cosine",
                spec=ServerlessSpec(
                    cloud="aws",
                    region="us-east-1"
                )
            )

            logger.info("⏳ Waiting 30 seconds for index to be ready...")
            time.sleep(30)
            index = pc.Index(index_name)
            logger.info("✅ Index created successfully")

        return index

    except ImportError:
        logger.error("❌ Pinecone package not installed!")
        logger.info("Run: pip install pinecone>=5.0.0")
        return False
    except Exception as e:
        logger.error(f"❌ Failed to setup Pinecone index: {e}")
        return False

def create_embeddings_openai(text: str):
    """Create embeddings using OpenAI (fallback)"""
    try:
        import openai
        api_key = os.getenv('OPENAI_API_KEY')
        if not api_key:
            raise ValueError("OpenAI API key required for embeddings")

        client = openai.OpenAI(api_key=api_key)
        response = client.embeddings.create(
            model="text-embedding-ada-002",
            input=text
        )
        return response.data[0].embedding
    except Exception as e:
        logger.error(f"Failed to create embeddings: {e}")
        raise

def upload_knowledge_base(index):
    """Upload knowledge base using manual embeddings approach"""
    try:
        # Load knowledge base
        knowledge_file = Path("output/chromadb_data/chunks_data.json")
        if not knowledge_file.exists():
            logger.error(f"❌ Knowledge base file not found: {knowledge_file}")
            return False

        logger.info(f"📚 Loading knowledge base from: {knowledge_file}")
        with open(knowledge_file, 'r', encoding='utf-8') as f:
            data = json.load(f)

        chunks = data.get('chunks', [])
        if not chunks:
            logger.error("❌ No chunks found in knowledge base")
            return False

        logger.info(f"📊 Processing {len(chunks)} chunks")

        # Check if already uploaded
        stats = index.describe_index_stats()
        namespace = os.getenv('PINECONE_NAMESPACE', 'management-knowledge')

        if stats.total_vector_count >= len(chunks):
            logger.info(f"✅ Knowledge base already uploaded: {stats.total_vector_count} vectors")
            return True

        # Check if we have OpenAI for embeddings
        openai_key = os.getenv('OPENAI_API_KEY')
        if not openai_key:
            logger.error("❌ OPENAI_API_KEY required for embeddings!")
            logger.info("Please add your OpenAI API key to .env file:")
            logger.info("OPENAI_API_KEY=your_openai_api_key")
            return False

        # Upload in batches with manual embeddings
        batch_size = 50  # Smaller batches for reliability
        total_uploaded = 0

        for i in range(0, len(chunks), batch_size):
            batch = chunks[i:i + batch_size]
            vectors = []

            logger.info(f"🔄 Processing batch {i//batch_size + 1}/{(len(chunks) + batch_size - 1)//batch_size}")

            for chunk in batch:
                try:
                    # Create embedding
                    embedding = create_embeddings_openai(chunk['content'])

                    # Prepare metadata
                    metadata = {
                        'source_file': chunk['metadata'].get('source_file', 'Unknown')[:50],
                        'framework': chunk['metadata'].get('framework', 'Unknown')[:50],
                        'category': chunk['metadata'].get('category', 'General')[:50],
                        'content': chunk['content'][:1000]  # Store content in metadata
                    }

                    vectors.append({
                        'id': chunk['id'],
                        'values': embedding,
                        'metadata': metadata
                    })

                except Exception as e:
                    logger.error(f"❌ Failed to process chunk {chunk['id']}: {e}")
                    continue

            if vectors:
                # Upload batch using traditional upsert
                index.upsert(vectors=vectors, namespace=namespace)
                total_uploaded += len(vectors)
                logger.info(f"✅ Uploaded {len(vectors)} vectors. Total: {total_uploaded}/{len(chunks)}")

                # Rate limiting
                time.sleep(2)

        logger.info(f"🎉 Successfully uploaded {total_uploaded} chunks to namespace '{namespace}'")

        # Final verification
        final_stats = index.describe_index_stats()
        logger.info(f"📊 Final stats: {final_stats.total_vector_count} total vectors")

        return True

    except Exception as e:
        logger.error(f"❌ Failed to upload knowledge base: {e}")
        return False

def test_search(index):
    """Test the search functionality"""
    try:
        namespace = os.getenv('PINECONE_NAMESPACE', 'management-knowledge')

        # Create test query embedding
        test_query = "How do I give difficult feedback?"
        query_embedding = create_embeddings_openai(test_query)

        # Search
        results = index.query(
            vector=query_embedding,
            top_k=3,
            include_metadata=True,
            namespace=namespace
        )

        if results.matches:
            logger.info(f"🔍 Search test successful! Found {len(results.matches)} results:")
            for i, match in enumerate(results.matches, 1):
                score = match.score
                source = match.metadata.get('source_file', 'Unknown')
                logger.info(f"  {i}. Score: {score:.3f} | Source: {source}")
            return True
        else:
            logger.warning("⚠️ Search test returned no results")
            return False

    except Exception as e:
        logger.error(f"❌ Search test failed: {e}")
        return False

def main():
    """Main setup function"""
    try:
        logger.info("🚀 Starting simple Pinecone setup...")

        # Load environment
        load_environment()

        # Check required keys
        required_keys = ['PINECONE_API_KEY', 'ANTHROPIC_API_KEY']
        missing_keys = [key for key in required_keys if not os.getenv(key)]

        if missing_keys:
            logger.error(f"❌ Missing required API keys: {missing_keys}")
            logger.info("Please edit your .env file and add the missing keys")
            return

        # Setup index
        index = setup_pinecone_index()
        if not index:
            logger.error("❌ Failed to setup Pinecone index")
            return

        # Upload knowledge base
        if not upload_knowledge_base(index):
            logger.error("❌ Failed to upload knowledge base")
            return

        # Test search
        if test_search(index):
            logger.info("🎉 Setup completed successfully!")
            logger.info("Your Pinecone RAG system is ready!")
        else:
            logger.warning("⚠️ Setup completed but search test failed")

    except Exception as e:
        logger.error(f"❌ Setup failed: {e}")

if __name__ == "__main__":
    main()
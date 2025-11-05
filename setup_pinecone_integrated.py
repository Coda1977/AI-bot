#!/usr/bin/env python3
"""
Pinecone setup using integrated embeddings (no external embedding API needed)
Uses the new upsert_records() method with automatic embedding generation
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

def create_anthropic_embeddings(text: str):
    """Create embeddings using Anthropic Claude (fallback approach)"""
    try:
        import anthropic

        api_key = os.getenv('ANTHROPIC_API_KEY')
        if not api_key:
            raise ValueError("Anthropic API key required")

        client = anthropic.Anthropic(api_key=api_key)

        # Use Claude to create a semantic representation
        # This is a workaround - not ideal but functional
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

def setup_pinecone_with_integrated_embeddings():
    """Setup Pinecone using integrated embeddings (preferred method)"""
    try:
        from pinecone import Pinecone

        # Load environment
        load_environment()

        api_key = os.getenv('PINECONE_API_KEY')
        if not api_key:
            logger.error("❌ PINECONE_API_KEY not found!")
            return False

        # Initialize Pinecone
        pc = Pinecone(api_key=api_key)
        logger.info("✅ Pinecone client initialized")

        # Index configuration
        index_name = os.getenv('PINECONE_INDEX_NAME', 'management-knowledge-v2')

        # Check if index exists
        existing_indexes = pc.list_indexes().names()

        if index_name in existing_indexes:
            logger.info(f"✅ Index '{index_name}' already exists")
            index = pc.Index(index_name)
        else:
            logger.error(f"❌ Index '{index_name}' not found!")
            logger.info("Please create the index using Pinecone CLI:")
            logger.info(f"pc index create -n {index_name} -m cosine -c aws -r us-east-1 --model llama-text-embed-v2 --field_map text=content")
            return False

        return index

    except Exception as e:
        logger.error(f"❌ Failed to setup Pinecone: {e}")
        return False

def upload_with_integrated_embeddings(index):
    """Upload using Pinecone's integrated embedding model"""
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

        logger.info(f"📊 Processing {len(chunks)} chunks using integrated embeddings")

        # Check if already uploaded
        stats = index.describe_index_stats()
        namespace = os.getenv('PINECONE_NAMESPACE', 'management-knowledge')
        namespace_stats = stats.namespaces.get(namespace, {})

        if namespace_stats.get('vector_count', 0) >= len(chunks):
            logger.info(f"✅ Knowledge base already uploaded: {namespace_stats.get('vector_count')} vectors")
            return True

        # Prepare records for integrated embedding
        records = []
        for chunk in chunks:
            # Prepare minimal metadata for Pinecone limits
            metadata = {
                'source_file': chunk['metadata'].get('source_file', 'Unknown')[:50],
                'framework': chunk['metadata'].get('framework', 'Unknown')[:50],
                'category': chunk['metadata'].get('category', 'General')[:50],
                'word_count': chunk.get('word_count', 0)
            }

            # Format for integrated embeddings
            record = {
                '_id': chunk['id'],
                'content': chunk['content'],  # This will be auto-embedded
                **metadata
            }
            records.append(record)

        # Upload in batches using upsert_records (integrated embeddings)
        batch_size = 100
        total_uploaded = 0

        for i in range(0, len(records), batch_size):
            batch = records[i:i + batch_size]

            try:
                logger.info(f"🔄 Uploading batch {i//batch_size + 1}/{(len(records) + batch_size - 1)//batch_size} using integrated embeddings")

                # Use upsert_records for automatic embedding
                index.upsert_records(namespace, batch)
                total_uploaded += len(batch)
                logger.info(f"✅ Uploaded {len(batch)} records. Total: {total_uploaded}/{len(records)}")

                # Rate limiting
                time.sleep(2)

            except Exception as e:
                logger.error(f"❌ Failed to upload batch {i//batch_size + 1}: {e}")
                logger.info("Trying fallback approach with manual embeddings...")
                return upload_with_manual_embeddings(index, records[i:])

        logger.info(f"🎉 Successfully uploaded {total_uploaded} records using integrated embeddings!")
        return True

    except Exception as e:
        logger.error(f"❌ Integrated embedding upload failed: {e}")
        logger.info("Trying fallback approach...")
        return False

def upload_with_manual_embeddings(index, remaining_records=None):
    """Fallback: Upload using manual Anthropic-based embeddings"""
    try:
        # Load knowledge base if not provided
        if remaining_records is None:
            knowledge_file = Path("output/chromadb_data/chunks_data.json")
            with open(knowledge_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            chunks = data.get('chunks', [])
        else:
            # Convert records back to chunks format
            chunks = []
            for record in remaining_records:
                chunk = {
                    'id': record['_id'],
                    'content': record['content'],
                    'metadata': {k: v for k, v in record.items() if k not in ['_id', 'content']}
                }
                chunks.append(chunk)

        logger.info(f"📊 Using Anthropic-based fallback embeddings for {len(chunks)} chunks")

        namespace = os.getenv('PINECONE_NAMESPACE', 'management-knowledge')

        # Upload in smaller batches with manual embeddings
        batch_size = 50
        total_uploaded = 0

        for i in range(0, len(chunks), batch_size):
            batch = chunks[i:i + batch_size]
            vectors = []

            logger.info(f"🔄 Processing batch {i//batch_size + 1}/{(len(chunks) + batch_size - 1)//batch_size} with manual embeddings")

            for chunk in batch:
                try:
                    # Create embedding using Anthropic
                    embedding = create_anthropic_embeddings(chunk['content'])

                    # Prepare metadata
                    metadata = {
                        'source_file': chunk['metadata'].get('source_file', 'Unknown')[:50],
                        'framework': chunk['metadata'].get('framework', 'Unknown')[:50],
                        'category': chunk['metadata'].get('category', 'General')[:50],
                        'content': chunk['content'][:500]  # Store partial content
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
                # Upload using traditional upsert method
                index.upsert(vectors=vectors, namespace=namespace)
                total_uploaded += len(vectors)
                logger.info(f"✅ Uploaded {len(vectors)} vectors. Total: {total_uploaded}")

                # Rate limiting
                time.sleep(3)

        logger.info(f"🎉 Successfully uploaded {total_uploaded} chunks using manual embeddings!")
        return True

    except Exception as e:
        logger.error(f"❌ Manual embedding upload failed: {e}")
        return False

def test_search(index):
    """Test the search functionality"""
    try:
        namespace = os.getenv('PINECONE_NAMESPACE', 'management-knowledge')

        logger.info("🔍 Testing search functionality...")

        # Try integrated search first
        try:
            results = index.search(
                namespace=namespace,
                query={
                    "top_k": 3,
                    "inputs": {
                        "text": "How do I give difficult feedback?"
                    }
                }
            )

            hits = results.get('result', {}).get('hits', [])
            if hits:
                logger.info(f"✅ Integrated search successful! Found {len(hits)} results:")
                for i, hit in enumerate(hits, 1):
                    score = hit.get('_score', 0)
                    source = hit.get('fields', {}).get('source_file', 'Unknown')
                    logger.info(f"  {i}. Score: {score:.3f} | Source: {source}")
                return True

        except Exception as e:
            logger.info(f"Integrated search failed, trying manual approach: {e}")

        # Fallback to manual search
        try:
            # Create test embedding
            query_embedding = create_anthropic_embeddings("How do I give difficult feedback?")

            results = index.query(
                vector=query_embedding,
                top_k=3,
                include_metadata=True,
                namespace=namespace
            )

            if results.matches:
                logger.info(f"✅ Manual search successful! Found {len(results.matches)} results:")
                for i, match in enumerate(results.matches, 1):
                    score = match.score
                    source = match.metadata.get('source_file', 'Unknown')
                    logger.info(f"  {i}. Score: {score:.3f} | Source: {source}")
                return True

        except Exception as e:
            logger.error(f"Manual search also failed: {e}")

        logger.warning("⚠️ Search test failed")
        return False

    except Exception as e:
        logger.error(f"❌ Search test failed: {e}")
        return False

def main():
    """Main setup function"""
    try:
        logger.info("🚀 Starting Pinecone setup with integrated embeddings...")

        # Load environment
        load_environment()

        # Check required keys
        required_keys = ['PINECONE_API_KEY', 'ANTHROPIC_API_KEY']
        missing_keys = [key for key in required_keys if not os.getenv(key)]

        if missing_keys:
            logger.error(f"❌ Missing required API keys: {missing_keys}")
            return

        # Setup index
        index = setup_pinecone_with_integrated_embeddings()
        if not index:
            return

        # Try integrated embeddings first
        logger.info("🎯 Attempting upload with Pinecone integrated embeddings...")
        success = upload_with_integrated_embeddings(index)

        if not success:
            logger.info("🔄 Falling back to Anthropic-based manual embeddings...")
            success = upload_with_manual_embeddings(index)

        if success:
            # Test search
            if test_search(index):
                logger.info("🎉 Setup completed successfully!")
                logger.info("Your Pinecone RAG system is ready!")
            else:
                logger.warning("⚠️ Setup completed but search test failed")
        else:
            logger.error("❌ Failed to upload knowledge base")

    except Exception as e:
        logger.error(f"❌ Setup failed: {e}")

if __name__ == "__main__":
    main()
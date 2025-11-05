#!/usr/bin/env python3
"""
Setup script for Pinecone knowledge base using 2025 API
Uses CLI for index creation and new upsert_records method
"""
import json
import os
import logging
import subprocess
import time
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

def check_cli_installed():
    """Check if Pinecone CLI is installed"""
    try:
        result = subprocess.run(['pc', 'version'], capture_output=True, text=True)
        if result.returncode == 0:
            logger.info(f"Pinecone CLI version: {result.stdout.strip()}")
            return True
        else:
            return False
    except FileNotFoundError:
        return False

def install_cli_instructions():
    """Provide CLI installation instructions"""
    logger.error("Pinecone CLI not found!")
    logger.info("Please install the Pinecone CLI:")
    logger.info("")
    logger.info("macOS (Homebrew):")
    logger.info("  brew tap pinecone-io/tap")
    logger.info("  brew install pinecone-io/tap/pinecone")
    logger.info("")
    logger.info("Other platforms:")
    logger.info("  Download from: https://github.com/pinecone-io/cli/releases")
    logger.info("")
    logger.info("After installation, run: pc version")

def configure_cli_auth():
    """Configure CLI authentication"""
    try:
        api_key = os.getenv('PINECONE_API_KEY')
        if not api_key:
            raise ValueError("PINECONE_API_KEY not found in environment variables")

        # Configure API key
        result = subprocess.run(
            ['pc', 'auth', 'configure', '--api-key', api_key],
            capture_output=True,
            text=True
        )

        if result.returncode == 0:
            logger.info("CLI authentication configured successfully")
            return True
        else:
            logger.error(f"CLI auth failed: {result.stderr}")
            return False

    except Exception as e:
        logger.error(f"Failed to configure CLI auth: {e}")
        return False

def create_pinecone_index():
    """Create Pinecone index using CLI with integrated embeddings"""
    try:
        index_name = os.getenv('PINECONE_INDEX_NAME', 'management-knowledge-v2')

        # Check if index already exists
        result = subprocess.run(['pc', 'index', 'list'], capture_output=True, text=True)
        if index_name in result.stdout:
            logger.info(f"Index '{index_name}' already exists")
            return True

        # Create index with integrated embedding model
        logger.info(f"Creating Pinecone index: {index_name}")

        create_cmd = [
            'pc', 'index', 'create',
            '-n', index_name,
            '-m', 'cosine',
            '-c', 'aws',
            '-r', 'us-east-1',
            '--model', 'llama-text-embed-v2',
            '--field_map', 'text=content'
        ]

        result = subprocess.run(create_cmd, capture_output=True, text=True)

        if result.returncode == 0:
            logger.info(f"Successfully created index: {index_name}")
            logger.info("Waiting 30 seconds for index to be ready...")
            time.sleep(30)
            return True
        else:
            logger.error(f"Index creation failed: {result.stderr}")
            return False

    except Exception as e:
        logger.error(f"Failed to create Pinecone index: {e}")
        return False

def upload_knowledge_base():
    """Upload the full knowledge base to Pinecone using 2025 API"""
    try:
        # Load environment
        load_environment()

        # Import current Pinecone SDK
        from pinecone import Pinecone

        api_key = os.getenv('PINECONE_API_KEY')
        if not api_key:
            raise ValueError("PINECONE_API_KEY not found in environment variables")

        # Initialize Pinecone client
        pc = Pinecone(api_key=api_key)
        index_name = os.getenv('PINECONE_INDEX_NAME', 'management-knowledge-v2')
        index = pc.Index(index_name)

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

        logger.info(f"Processing {len(chunks)} chunks for upload using 2025 API")

        # Check if already uploaded
        stats = index.describe_index_stats()
        namespace = os.getenv('PINECONE_NAMESPACE', 'management-knowledge')
        namespace_stats = stats.namespaces.get(namespace, {})

        if namespace_stats.get('vector_count', 0) >= len(chunks):
            logger.info(f"Knowledge base already uploaded: {namespace_stats.get('vector_count')} vectors in namespace '{namespace}'")
            return

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
                logger.info(f"Uploading batch {i//batch_size + 1}/{(len(records) + batch_size - 1)//batch_size}")

                # Use new upsert_records method with namespace
                index.upsert_records(namespace, batch)
                total_uploaded += len(batch)
                logger.info(f"Uploaded {len(batch)} records. Total: {total_uploaded}/{len(records)}")

                # Add delay to avoid rate limits
                time.sleep(2)

            except Exception as e:
                logger.error(f"Failed to upload batch {i//batch_size + 1}: {e}")
                continue

        logger.info(f"Successfully uploaded {total_uploaded} records to Pinecone namespace '{namespace}'")

        # Wait for indexing
        logger.info("Waiting 15 seconds for indexing to complete...")
        time.sleep(15)

        # Verify upload
        final_stats = index.describe_index_stats()
        final_namespace_stats = final_stats.namespaces.get(namespace, {})
        logger.info(f"Final namespace stats: {final_namespace_stats.get('vector_count', 0)} vectors in '{namespace}'")

    except Exception as e:
        logger.error(f"Failed to upload knowledge base: {e}")
        raise

def test_search():
    """Test the uploaded knowledge base with a sample search"""
    try:
        from pinecone import Pinecone

        api_key = os.getenv('PINECONE_API_KEY')
        pc = Pinecone(api_key=api_key)
        index_name = os.getenv('PINECONE_INDEX_NAME', 'management-knowledge-v2')
        index = pc.Index(index_name)
        namespace = os.getenv('PINECONE_NAMESPACE', 'management-knowledge')

        logger.info("Testing search functionality...")

        # Test search
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
            logger.info(f"✅ Search test successful! Found {len(hits)} results:")
            for i, hit in enumerate(hits, 1):
                score = hit.get('_score', 0)
                source = hit.get('fields', {}).get('source_file', 'Unknown')
                logger.info(f"  {i}. Score: {score:.3f} | Source: {source}")
        else:
            logger.warning("⚠️ Search test returned no results")

    except Exception as e:
        logger.error(f"Search test failed: {e}")

def main():
    """Main setup function using 2025 API"""
    try:
        logger.info("Starting Pinecone knowledge base setup using 2025 API...")

        # Load environment
        load_environment()

        # Check required environment variables
        required_vars = ['PINECONE_API_KEY']
        missing_vars = [var for var in required_vars if not os.getenv(var)]

        if missing_vars:
            logger.error(f"Missing required environment variables: {missing_vars}")
            logger.info("Please set these variables in your .env file:")
            for var in missing_vars:
                logger.info(f"  {var}=your_api_key_here")
            return

        # Check CLI installation
        if not check_cli_installed():
            install_cli_instructions()
            return

        # Configure CLI authentication
        if not configure_cli_auth():
            logger.error("Failed to configure CLI authentication")
            return

        # Create index using CLI
        if not create_pinecone_index():
            logger.error("Failed to create Pinecone index")
            return

        # Upload knowledge base using SDK
        upload_knowledge_base()

        # Test the setup
        test_search()

        logger.info("🚀 Pinecone setup completed successfully!")
        logger.info("Your RAG API v2.0 is ready to use with the full knowledge base.")
        logger.info(f"Index: {os.getenv('PINECONE_INDEX_NAME', 'management-knowledge-v2')}")
        logger.info(f"Namespace: {os.getenv('PINECONE_NAMESPACE', 'management-knowledge')}")

    except Exception as e:
        logger.error(f"Setup failed: {e}")
        raise

if __name__ == "__main__":
    main()
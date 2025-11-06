#!/usr/bin/env python3
"""
Rebuild knowledge base with proper semantic embeddings
Phase 1: Replace broken embeddings with real semantic embeddings
"""
import json
import os
from pathlib import Path
import time
from typing import List, Dict, Any

def create_proper_embeddings(text: str, method: str = "auto") -> List[float]:
    """Create proper semantic embeddings using best available method"""

    # Method 1: OpenAI (best quality)
    if method in ["auto", "openai"]:
        try:
            import openai
            api_key = os.getenv('OPENAI_API_KEY')
            if api_key and api_key != "your_openai_api_key_here":
                client = openai.OpenAI(api_key=api_key)
                response = client.embeddings.create(
                    model="text-embedding-ada-002",
                    input=text[:8000]  # OpenAI limit
                )
                print(f"✅ Using OpenAI embeddings")
                return response.data[0].embedding
        except Exception as e:
            if method == "openai":
                raise e
            print(f"⚠️ OpenAI not available: {e}")

    # Method 2: Sentence Transformers (good quality, no API key needed)
    if method in ["auto", "sentence_transformers"]:
        try:
            from sentence_transformers import SentenceTransformer
            # Use a model optimized for semantic search
            model = SentenceTransformer('all-MiniLM-L6-v2')
            embedding = model.encode(text)
            print(f"✅ Using Sentence Transformers embeddings")
            return embedding.tolist()
        except ImportError:
            if method == "sentence_transformers":
                raise ImportError("sentence-transformers not installed. Run: pip install sentence-transformers")
            print(f"⚠️ Sentence Transformers not available")

    # Method 3: Cohere (alternative API)
    if method in ["auto", "cohere"]:
        try:
            import cohere
            api_key = os.getenv('COHERE_API_KEY')
            if api_key:
                co = cohere.Client(api_key)
                response = co.embed(texts=[text], model='embed-english-v2.0')
                print(f"✅ Using Cohere embeddings")
                return response.embeddings[0]
        except Exception as e:
            if method == "cohere":
                raise e
            print(f"⚠️ Cohere not available: {e}")

    raise ValueError("No embedding method available. Install sentence-transformers or provide OpenAI/Cohere API key")

def clear_pinecone_namespace():
    """Clear existing vectors from Pinecone namespace"""
    try:
        from pinecone import Pinecone
        api_key = os.getenv('PINECONE_API_KEY')
        if not api_key:
            raise ValueError("PINECONE_API_KEY required")

        pc = Pinecone(api_key=api_key)
        index = pc.Index('management-knowledge-v2')
        namespace = "management-knowledge"

        print("🗑️ Clearing existing vectors from Pinecone...")

        # Get all vector IDs
        stats = index.describe_index_stats()
        vector_count = stats.namespaces.get(namespace, {}).get('vector_count', 0)

        if vector_count > 0:
            # Delete all vectors in namespace
            index.delete(delete_all=True, namespace=namespace)
            print(f"✅ Cleared {vector_count} vectors from namespace '{namespace}'")

            # Wait for deletion to complete
            time.sleep(5)
        else:
            print("ℹ️ Namespace already empty")

        return True
    except Exception as e:
        print(f"❌ Failed to clear namespace: {e}")
        return False

def rebuild_knowledge_base():
    """Rebuild entire knowledge base with proper embeddings"""
    try:
        print("🚀 Starting knowledge base rebuild with proper embeddings...")

        # Load all content
        chunks_file = Path("output/chromadb_data/chunks_data.json")
        if not chunks_file.exists():
            raise FileNotFoundError(f"Knowledge base file not found: {chunks_file}")

        with open(chunks_file, 'r', encoding='utf-8') as f:
            data = json.load(f)

        chunks = data.get('chunks', [])
        print(f"📊 Found {len(chunks)} chunks to process")

        # Clear existing vectors
        if not clear_pinecone_namespace():
            raise Exception("Failed to clear existing vectors")

        # Initialize Pinecone
        from pinecone import Pinecone
        api_key = os.getenv('PINECONE_API_KEY')
        pc = Pinecone(api_key=api_key)
        index = pc.Index('management-knowledge-v2')
        namespace = "management-knowledge"

        # Process chunks in batches
        batch_size = 50
        vectors_to_upload = []
        total_processed = 0

        for i, chunk in enumerate(chunks):
            try:
                print(f"🔄 Processing chunk {i+1}/{len(chunks)}: {chunk['id']}")

                # Create proper embeddings
                content = chunk['content']
                embedding = create_proper_embeddings(content)

                # Prepare vector
                vector = {
                    'id': chunk['id'],
                    'values': embedding,
                    'metadata': {
                        'content': content[:8000],  # Store content in metadata
                        'source_file': chunk['metadata'].get('source_file', 'Unknown'),
                        'framework': chunk['metadata'].get('framework', 'Unknown'),
                        'category': chunk['metadata'].get('category', 'General'),
                        'section': chunk['metadata'].get('section', ''),
                        'word_count': chunk.get('word_count', 0),
                        'char_count': chunk.get('char_count', 0),
                        'chunk_type': chunk['metadata'].get('chunk_type', 'standard'),
                        'language': chunk['metadata'].get('language', 'english')
                    }
                }
                vectors_to_upload.append(vector)
                total_processed += 1

                # Upload in batches
                if len(vectors_to_upload) >= batch_size or i == len(chunks) - 1:
                    print(f"⬆️ Uploading batch of {len(vectors_to_upload)} vectors...")
                    index.upsert(vectors=vectors_to_upload, namespace=namespace)
                    vectors_to_upload = []

                    # Rate limiting
                    time.sleep(1)

            except Exception as e:
                print(f"❌ Failed to process chunk {chunk['id']}: {e}")
                continue

        print(f"🎉 Successfully rebuilt knowledge base!")
        print(f"✅ Processed: {total_processed}/{len(chunks)} chunks")

        # Verify the upload
        time.sleep(5)
        stats = index.describe_index_stats()
        final_count = stats.namespaces.get(namespace, {}).get('vector_count', 0)
        print(f"✅ Final vector count in Pinecone: {final_count}")

        return True

    except Exception as e:
        print(f"❌ Knowledge base rebuild failed: {e}")
        return False

def test_rebuilt_search():
    """Test the rebuilt search with key queries"""
    test_queries = [
        "giving feedback SBI situation behavior impact",
        "radical candor feedback framework",
        "coaching conversations development",
        "delegation authority levels",
        "1:1 meetings framework",
        "difficult feedback conversations"
    ]

    print("🧪 Testing rebuilt search system...")

    try:
        import requests
        api_url = "https://ai-bot-nine-chi.vercel.app/api/search"

        for query in test_queries:
            print(f"\n🔍 Testing: '{query}'")

            response = requests.post(api_url, json={"query": query, "top_k": 3})
            if response.status_code == 200:
                data = response.json()
                results = data.get('results', [])
                print(f"  Found {len(results)} results")

                for i, result in enumerate(results[:2]):
                    source = result['metadata']['source_file']
                    score = result['score']
                    print(f"    {i+1}. {source} (score: {score:.3f})")
            else:
                print(f"  ❌ API error: {response.status_code}")

        print("\n✅ Search testing completed")

    except Exception as e:
        print(f"❌ Search testing failed: {e}")

if __name__ == "__main__":
    print("=" * 60)
    print("🎯 KNOWLEDGE BASE REBUILD - PHASE 1")
    print("Replacing broken embeddings with proper semantic embeddings")
    print("=" * 60)

    # Check dependencies
    try:
        import sentence_transformers
        print("✅ sentence-transformers available")
    except ImportError:
        print("❌ sentence-transformers not installed")
        print("Installing sentence-transformers...")
        import subprocess
        subprocess.check_call(["pip", "install", "sentence-transformers"])

    # Run rebuild
    success = rebuild_knowledge_base()

    if success:
        print("\n" + "=" * 60)
        print("🎉 PHASE 1 COMPLETED SUCCESSFULLY!")
        print("Knowledge base rebuilt with proper embeddings")
        print("=" * 60)

        # Test the results
        print("\nWaiting 30 seconds for API deployment...")
        time.sleep(30)
        test_rebuilt_search()
    else:
        print("\n" + "=" * 60)
        print("❌ PHASE 1 FAILED")
        print("Knowledge base rebuild unsuccessful")
        print("=" * 60)
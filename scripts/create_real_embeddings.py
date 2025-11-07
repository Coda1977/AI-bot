#!/usr/bin/env python3
"""
Create REAL Embeddings for Knowledge Base
Replaces fake embeddings with real OpenAI embeddings
"""
import json
import os
import sys
from pathlib import Path
from typing import List, Dict
import time

# Add parent directory to path
sys.path.append(str(Path(__file__).parent.parent))

def load_chunks(chunks_file: Path) -> List[Dict]:
    """Load chunks from JSON file"""
    print(f"📂 Loading chunks from {chunks_file}...")

    if chunks_file.suffix == '.gz':
        import gzip
        with gzip.open(chunks_file, 'rt', encoding='utf-8') as f:
            data = json.load(f)
    else:
        with open(chunks_file, 'r', encoding='utf-8') as f:
            data = json.load(f)

    chunks = data.get('chunks', [])
    print(f"✅ Loaded {len(chunks)} chunks")
    return chunks


def create_real_embeddings(chunks: List[Dict]) -> List[Dict]:
    """
    Create REAL embeddings using OpenAI
    Returns chunks with embeddings added
    """
    from openai import OpenAI

    api_key = os.getenv('OPENAI_API_KEY')
    if not api_key:
        raise ValueError("OPENAI_API_KEY environment variable not set!")

    client = OpenAI(api_key=api_key)

    print(f"\n🔄 Creating real embeddings for {len(chunks)} chunks...")
    print("Using OpenAI text-embedding-3-small (cost: ~$0.02 per 1M tokens)")

    chunks_with_embeddings = []
    batch_size = 100  # Process in batches to show progress

    for i in range(0, len(chunks), batch_size):
        batch = chunks[i:i + batch_size]

        # Prepare texts for embedding
        texts = [chunk['content'] for chunk in batch]

        try:
            # Create embeddings (all at once for efficiency)
            print(f"  Processing batch {i//batch_size + 1}/{(len(chunks)-1)//batch_size + 1}...")

            response = client.embeddings.create(
                model="text-embedding-3-small",  # 1536 dimensions, cheaper
                input=texts
            )

            # Add embeddings to chunks
            for j, chunk in enumerate(batch):
                embedding = response.data[j].embedding
                chunk['embedding'] = embedding
                chunks_with_embeddings.append(chunk)

            # Rate limiting: sleep a bit between batches
            if i + batch_size < len(chunks):
                time.sleep(0.5)

        except Exception as e:
            print(f"❌ Error processing batch: {e}")
            raise

    print(f"✅ Created {len(chunks_with_embeddings)} embeddings")
    return chunks_with_embeddings


def upload_to_pinecone(chunks: List[Dict], namespace: str = "management-knowledge"):
    """Upload chunks with real embeddings to Pinecone"""
    from pinecone import Pinecone

    api_key = os.getenv('PINECONE_API_KEY')
    if not api_key:
        raise ValueError("PINECONE_API_KEY environment variable not set!")

    index_name = os.getenv('PINECONE_INDEX_NAME', 'management-knowledge-v2')

    print(f"\n🔄 Connecting to Pinecone index '{index_name}'...")
    pc = Pinecone(api_key=api_key)
    index = pc.Index(index_name)

    # Check current stats
    stats = index.describe_index_stats()
    print(f"📊 Current index stats: {stats.total_vector_count} total vectors")

    print(f"\n🔄 Uploading {len(chunks)} vectors to namespace '{namespace}'...")

    # Prepare vectors for upload
    batch_size = 100
    for i in range(0, len(chunks), batch_size):
        batch = chunks[i:i + batch_size]

        vectors = []
        for chunk in batch:
            # Store metadata (Pinecone limit: 40KB per vector)
            # Store more content to reduce dependency on local cache
            content_text = chunk['content']

            # Try to store full content if small enough, otherwise store substantial preview
            # Aim for ~3000 chars (leaves room for other metadata within 40KB limit)
            if len(content_text) <= 3000:
                stored_content = content_text
            else:
                # Store first 3000 chars with ellipsis
                stored_content = content_text[:2997] + "..."

            vectors.append({
                "id": chunk['id'],
                "values": chunk['embedding'],
                "metadata": {
                    "source_file": chunk['metadata'].get('source_file', '')[:200],
                    "framework": chunk['metadata'].get('framework', '')[:100],
                    "category": chunk['metadata'].get('category', '')[:100],
                    "section": chunk['metadata'].get('section', '')[:200],
                    "word_count": chunk.get('word_count', 0),
                    "content": stored_content,  # Full content or substantial preview
                    "content_truncated": len(content_text) > 3000
                }
            })

        try:
            index.upsert(vectors=vectors, namespace=namespace)
            print(f"  Uploaded batch {i//batch_size + 1}/{(len(chunks)-1)//batch_size + 1}")
            time.sleep(0.5)  # Rate limiting
        except Exception as e:
            print(f"❌ Error uploading batch: {e}")
            raise

    print(f"✅ Upload complete!")

    # Verify
    time.sleep(2)  # Wait for index to update
    stats = index.describe_index_stats()
    namespace_stats = stats.namespaces.get(namespace, {})
    print(f"\n📊 Final stats for namespace '{namespace}':")
    print(f"   Vectors: {namespace_stats.get('vector_count', 0)}")


def save_embeddings_locally(chunks: List[Dict], output_file: Path):
    """Save chunks with embeddings to local file"""
    print(f"\n💾 Saving embeddings to {output_file}...")

    data = {"chunks": chunks}

    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2)

    file_size_mb = output_file.stat().st_size / (1024 * 1024)
    print(f"✅ Saved {len(chunks)} chunks with embeddings ({file_size_mb:.2f} MB)")


def main():
    print("=" * 60)
    print("  REAL EMBEDDINGS GENERATOR")
    print("  Replacing fake embeddings with OpenAI embeddings")
    print("=" * 60)

    # Check environment variables
    if not os.getenv('OPENAI_API_KEY'):
        print("\n❌ ERROR: OPENAI_API_KEY not set!")
        print("   Set it with: export OPENAI_API_KEY='sk-...'")
        return

    if not os.getenv('PINECONE_API_KEY'):
        print("\n❌ ERROR: PINECONE_API_KEY not set!")
        print("   Set it with: export PINECONE_API_KEY='...'")
        return

    # Load existing chunks
    chunks_file = Path("chunks_data.json")
    if not chunks_file.exists():
        chunks_file = Path("chunks_data.json.gz")

    if not chunks_file.exists():
        print(f"\n❌ ERROR: Could not find chunks_data.json or chunks_data.json.gz")
        return

    chunks = load_chunks(chunks_file)

    # Create real embeddings
    chunks_with_embeddings = create_real_embeddings(chunks)

    # Save locally (for backup and local testing)
    output_file = Path("chunks_with_real_embeddings.json")
    save_embeddings_locally(chunks_with_embeddings, output_file)

    # Upload to Pinecone
    namespace = os.getenv('PINECONE_NAMESPACE', 'management-knowledge')
    upload_to_pinecone(chunks_with_embeddings, namespace)

    print("\n" + "=" * 60)
    print("✅ SUCCESS! Real embeddings created and uploaded")
    print("=" * 60)
    print("\nNext steps:")
    print("1. Update your API to use vector similarity search")
    print("2. Test search quality")
    print("3. Deploy to production")
    print(f"\nCost estimate: ~$0.02-0.05 (one-time)")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n⚠️  Interrupted by user")
    except Exception as e:
        print(f"\n\n❌ ERROR: {e}")
        import traceback
        traceback.print_exc()

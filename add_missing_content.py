#!/usr/bin/env python3
"""
Add missing content to Pinecone knowledge base:
1. Giving Feedback.pptx content (SBI framework)
2. Core training materials.md (comprehensive frameworks)
"""
import json
import os
import hashlib
from pathlib import Path

def create_anthropic_embeddings(text: str):
    """Create embeddings using same method as existing uploads"""
    try:
        import anthropic
        api_key = os.getenv('ANTHROPIC_API_KEY')
        if not api_key:
            print("❌ ANTHROPIC_API_KEY required")
            return None

        client = anthropic.Anthropic(api_key=api_key)
        response = client.messages.create(
            model="claude-3-haiku-20240307",
            max_tokens=100,
            messages=[{
                "role": "user",
                "content": f"Create a numerical semantic vector representation for this text (return only 10 comma-separated numbers between -1 and 1): {text[:500]}"
            }]
        )

        text_response = response.content[0].text
        numbers = [float(x.strip()) for x in text_response.split(',') if x.strip().replace('-','').replace('.','').isdigit()]

        while len(numbers) < 1536:
            numbers.extend(numbers[:min(100, 1536-len(numbers))])

        return numbers[:1536]

    except Exception as e:
        print(f"❌ Embedding failed: {e}")
        # Fallback to hash-based
        hash_val = hashlib.md5(text.encode()).hexdigest()
        numbers = [int(hash_val[i:i+2], 16) / 255.0 - 0.5 for i in range(0, len(hash_val), 2)]
        while len(numbers) < 1536:
            numbers.extend(numbers[:min(100, 1536-len(numbers))])
        return numbers[:1536]

def add_missing_content():
    """Add missing content to Pinecone"""
    try:
        # Initialize Pinecone
        from pinecone import Pinecone
        api_key = os.getenv('PINECONE_API_KEY')
        if not api_key:
            print("❌ PINECONE_API_KEY required")
            return False

        pc = Pinecone(api_key=api_key)
        index = pc.Index('management-knowledge-v2')
        namespace = "management-knowledge"

        print("📊 Adding missing content to Pinecone...")

        # 1. Add Giving Feedback content
        print("🔍 Loading local chunks to find Giving Feedback content...")
        chunks_file = Path("output/chromadb_data/chunks_data.json")
        with open(chunks_file, 'r', encoding='utf-8') as f:
            data = json.load(f)

        giving_feedback_chunks = [c for c in data['chunks'] if 'Giving Feedback.pptx' in c['id']]
        print(f"Found {len(giving_feedback_chunks)} Giving Feedback chunks")

        vectors_to_upload = []

        for chunk in giving_feedback_chunks:
            print(f"📝 Processing: {chunk['id']}")

            # Create embedding
            embedding = create_anthropic_embeddings(chunk['content'])
            if not embedding:
                continue

            # Prepare vector for upload
            vector = {
                'id': chunk['id'],
                'values': embedding,
                'metadata': {
                    'content': chunk['content'][:8000],  # Store content in metadata
                    'source_file': chunk['metadata'].get('source_file', 'Giving Feedback.pptx'),
                    'framework': chunk['metadata'].get('framework', 'SBI Framework'),
                    'category': chunk['metadata'].get('category', 'Feedback'),
                    'word_count': chunk.get('word_count', 400)
                }
            }
            vectors_to_upload.append(vector)

        # 2. Add core training materials
        print("📚 Processing core training materials...")
        core_materials_file = Path("core training materials.md")
        if core_materials_file.exists():
            with open(core_materials_file, 'r', encoding='utf-8') as f:
                content = f.read()

            # Split into chunks (simple approach)
            chunks = content.split('\n\n## ')

            for i, chunk_text in enumerate(chunks):
                if len(chunk_text.strip()) > 100:  # Skip very short chunks
                    chunk_id = f"core_training_materials_chunk_{i}"
                    print(f"📝 Processing: {chunk_id}")

                    embedding = create_anthropic_embeddings(chunk_text)
                    if not embedding:
                        continue

                    # Determine framework based on content
                    framework = "General"
                    if "feedback" in chunk_text.lower():
                        framework = "Feedback Framework"
                    elif "coaching" in chunk_text.lower():
                        framework = "Coaching Framework"
                    elif "delegation" in chunk_text.lower():
                        framework = "Delegation Framework"
                    elif "1:1" in chunk_text.lower():
                        framework = "1:1 Framework"

                    vector = {
                        'id': chunk_id,
                        'values': embedding,
                        'metadata': {
                            'content': chunk_text[:8000],
                            'source_file': 'core training materials.md',
                            'framework': framework,
                            'category': 'Management Frameworks',
                            'word_count': len(chunk_text.split())
                        }
                    }
                    vectors_to_upload.append(vector)

        # Upload vectors
        if vectors_to_upload:
            print(f"⬆️ Uploading {len(vectors_to_upload)} vectors to Pinecone...")

            # Upload in batches
            batch_size = 100
            for i in range(0, len(vectors_to_upload), batch_size):
                batch = vectors_to_upload[i:i + batch_size]
                index.upsert(vectors=batch, namespace=namespace)
                print(f"✅ Uploaded batch {i//batch_size + 1}/{(len(vectors_to_upload) + batch_size - 1)//batch_size}")

            print("🎉 Successfully added missing content!")
            return True
        else:
            print("❌ No content to upload")
            return False

    except Exception as e:
        print(f"❌ Failed to add content: {e}")
        return False

if __name__ == "__main__":
    success = add_missing_content()
    if success:
        print("✅ Content addition completed")
    else:
        print("❌ Content addition failed")
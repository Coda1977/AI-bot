#!/usr/bin/env python3
"""
Compress knowledge base for Vercel deployment
"""

import json
import gzip
from pathlib import Path

def compress_knowledge_base():
    """Compress the chunks_data.json for smaller deployment"""

    # Load original data
    with open('chunks_data.json', 'r', encoding='utf-8') as f:
        data = json.load(f)

    chunks = data.get('chunks', [])
    print(f"Original chunks: {len(chunks)}")

    # Create compressed version with essential data only
    compressed_chunks = []
    for chunk in chunks:
        compressed_chunk = {
            'id': chunk['id'],
            'content': chunk['content'],
            'source_file': chunk['metadata'].get('source_file', 'Unknown'),
            'framework': chunk['metadata'].get('framework', 'Unknown'),
            'category': chunk['metadata'].get('category', 'General')
        }
        compressed_chunks.append(compressed_chunk)

    # Save compressed version
    compressed_data = {'chunks': compressed_chunks}

    # Save as regular JSON
    with open('chunks_compressed.json', 'w', encoding='utf-8') as f:
        json.dump(compressed_data, f, separators=(',', ':'))

    # Also save as gzipped version
    with gzip.open('chunks_compressed.json.gz', 'wt', encoding='utf-8') as f:
        json.dump(compressed_data, f, separators=(',', ':'))

    # Check sizes
    original_size = Path('chunks_data.json').stat().st_size
    compressed_size = Path('chunks_compressed.json').stat().st_size
    gzipped_size = Path('chunks_compressed.json.gz').stat().st_size

    print(f"Original size: {original_size:,} bytes ({original_size/1024/1024:.1f} MB)")
    print(f"Compressed size: {compressed_size:,} bytes ({compressed_size/1024/1024:.1f} MB)")
    print(f"Gzipped size: {gzipped_size:,} bytes ({gzipped_size/1024/1024:.1f} MB)")
    print(f"Space saved: {(original_size - gzipped_size)/original_size*100:.1f}%")

if __name__ == "__main__":
    compress_knowledge_base()
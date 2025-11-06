# Real Embeddings Setup

## What This Does

Replaces the **fake embeddings** in Pinecone with **real OpenAI embeddings**.

**Before:** Random numbers that gave random search results
**After:** Semantic embeddings that give accurate, relevant results

---

## Prerequisites

1. **API Keys** (set as environment variables):
   ```bash
   export OPENAI_API_KEY="sk-..."
   export PINECONE_API_KEY="..."
   export PINECONE_INDEX_NAME="management-knowledge-v2"  # optional
   export PINECONE_NAMESPACE="management-knowledge"      # optional
   ```

2. **Python packages** (already in requirements.txt):
   ```bash
   pip install openai pinecone
   ```

---

## How to Run

### Step 1: Set API Keys

```bash
# OpenAI (for creating embeddings)
export OPENAI_API_KEY="sk-proj-..."

# Pinecone (for storing vectors)
export PINECONE_API_KEY="your-pinecone-key"
```

### Step 2: Run the Script

```bash
cd /home/user/AI-bot
python3 scripts/create_real_embeddings.py
```

### Step 3: What Happens

The script will:
1. ✅ Load your 816 chunks from `chunks_data.json`
2. ✅ Create real embeddings using OpenAI (text-embedding-3-small)
3. ✅ Save locally to `chunks_with_real_embeddings.json` (backup)
4. ✅ Upload to Pinecone with real embeddings

**Time:** ~2-3 minutes for 816 chunks
**Cost:** ~$0.02-0.05 (one-time)

---

## Expected Output

```
============================================================
  REAL EMBEDDINGS GENERATOR
  Replacing fake embeddings with OpenAI embeddings
============================================================

📂 Loading chunks from chunks_data.json...
✅ Loaded 816 chunks

🔄 Creating real embeddings for 816 chunks...
Using OpenAI text-embedding-3-small (cost: ~$0.02 per 1M tokens)
  Processing batch 1/9...
  Processing batch 2/9...
  ...
✅ Created 816 embeddings

💾 Saving embeddings to chunks_with_real_embeddings.json...
✅ Saved 816 chunks with embeddings (45.2 MB)

🔄 Connecting to Pinecone index 'management-knowledge-v2'...
📊 Current index stats: 817 total vectors

🔄 Uploading 816 vectors to namespace 'management-knowledge'...
  Uploaded batch 1/9
  Uploaded batch 2/9
  ...
✅ Upload complete!

📊 Final stats for namespace 'management-knowledge':
   Vectors: 816

============================================================
✅ SUCCESS! Real embeddings created and uploaded
============================================================

Next steps:
1. Update your API to use vector similarity search
2. Test search quality
3. Deploy to production

Cost estimate: ~$0.02-0.05 (one-time)
```

---

## Verify It Worked

### Test the API:

```bash
# Check health (should show vector_search: true)
curl https://ai-bot-nine-chi.vercel.app/api/health

# Test search
curl -X POST https://ai-bot-nine-chi.vercel.app/api/search \
  -H "Content-Type: application/json" \
  -d '{
    "query": "giving feedback SBI",
    "top_k": 3
  }'
```

You should see:
- Results about Situation-Behavior-Impact feedback
- High similarity scores (0.7-0.9)
- Relevant content (not random)

---

## Troubleshooting

### Error: "OPENAI_API_KEY not set"
```bash
export OPENAI_API_KEY="sk-..."
```

### Error: "PINECONE_API_KEY not set"
```bash
export PINECONE_API_KEY="your-key"
```

### Error: "Could not find chunks_data.json"
Make sure you're running from the project root:
```bash
cd /home/user/AI-bot
python3 scripts/create_real_embeddings.py
```

### Want to use a different embedding model?
Edit the script and change:
```python
model="text-embedding-3-small"  # 1536 dims, $0.02/1M tokens
```

To:
```python
model="text-embedding-3-large"   # 3072 dims, $0.13/1M tokens (better quality)
```

---

## What Changed in the API

The API now:
1. **Creates real query embeddings** using OpenAI
2. **Searches Pinecone** with vector similarity (not fake vectors!)
3. **Falls back to keyword search** if OpenAI/Pinecone unavailable

**Hybrid Architecture:**
```
Query → OpenAI embedding → Pinecone vector search → Results
        (if unavailable) → Keyword search → Results
```

---

## Cost Breakdown

**One-time costs:**
- Creating embeddings: ~$0.02-0.05 for 816 chunks

**Per-query costs:**
- Query embedding: $0.000013 per search
- Pinecone search: ~$0.0001 per search
- **Total: ~$0.00011 per search (0.01 cents)**

**For 10,000 searches/month: ~$1.30**

Your pricing ($15,000/year) = **99.3% profit margin** 🎯

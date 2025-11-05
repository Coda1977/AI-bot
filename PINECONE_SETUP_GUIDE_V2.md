# Pinecone RAG API v2.0 Setup Guide (2025 API)

## 🚀 Updated for Current Pinecone API

This guide uses the **current 2025 Pinecone API** with integrated embeddings, CLI-based index creation, and modern best practices.

## Key Changes from Previous Version

### ✅ **What's New:**
- **Correct Package**: `pinecone` (not `pinecone-client`)
- **CLI Index Creation**: Uses `pc index create` with integrated embeddings
- **Integrated Embeddings**: Built-in `llama-text-embed-v2` model
- **Modern API**: `upsert_records()` method with automatic embedding
- **Namespace Support**: Better multi-tenant data isolation

### ❌ **What's Deprecated:**
- `pinecone-client` package (old)
- Manual embedding creation with OpenAI
- `index.upsert()` method (old)
- Complex vector format requirements

## Prerequisites

### 1. Pinecone Account Setup
1. Go to [https://app.pinecone.io/](https://app.pinecone.io/)
2. Sign up for free account (2GB storage, 2M vectors)
3. Get your API key from the dashboard

### 2. Install Pinecone CLI

**macOS (Homebrew):**
```bash
brew tap pinecone-io/tap
brew install pinecone-io/tap/pinecone

# Verify installation
pc version
```

**Other platforms:**
Download from [GitHub Releases](https://github.com/pinecone-io/cli/releases) (Linux, Windows, macOS)

### 3. API Keys Required
- **Pinecone API Key**: For vector database and embeddings
- **Anthropic API Key**: For AI responses (Claude 3.5 Sonnet)
- **OpenAI API Key**: Optional backup for AI responses

## Setup Steps

### Step 1: Configure Environment Variables

Create `.env` file with your API keys:

```bash
# Copy the example file
cp .env.pinecone.example .env

# Edit with your actual API keys
PINECONE_API_KEY=your_pinecone_api_key_here
ANTHROPIC_API_KEY=your_anthropic_api_key_here
OPENAI_API_KEY=your_openai_api_key_here  # Optional backup

# Optional customization
PINECONE_INDEX_NAME=management-knowledge-v2
PINECONE_NAMESPACE=management-knowledge
```

### Step 2: Install Dependencies (Current API)

```bash
# Install current Pinecone SDK and dependencies
pip install -r requirements.txt
```

### Step 3: Run Automated Setup

```bash
# Run the v2.0 setup script
python setup_pinecone_v2.py
```

This script will:
1. ✅ Check CLI installation
2. ✅ Configure CLI authentication
3. ✅ Create index with integrated embeddings (`llama-text-embed-v2`)
4. ✅ Upload 816 knowledge chunks using `upsert_records()`
5. ✅ Test search functionality
6. ✅ Verify complete setup

### Step 4: Test API Locally

```bash
# Start the v2.0 API server
python api/pinecone_rag_v2.py
```

Test endpoints:
- Health check: http://localhost:8000/api/health
- Search: POST to http://localhost:8000/api/search
- Ask: POST to http://localhost:8000/api/ask

## API Changes in v2.0

### Search Request Format
```json
{
  "query": "How do I give difficult feedback?",
  "top_k": 5,
  "namespace": "management-knowledge"
}
```

### Response Format (Updated)
```json
{
  "results": [
    {
      "id": "chunk_id",
      "content": "Full content...",
      "metadata": {
        "source_file": "Giving Feedback.pptx",
        "framework": "SBI Model",
        "category": "Feedback",
        "word_count": 400
      },
      "score": 0.95
    }
  ],
  "total_results": 5,
  "query": "How do I give difficult feedback?"
}
```

## Deployment to Vercel

### Step 1: Update Main API File

Replace the old API with the v2.0 version:

```bash
# Replace the main API file
cp api/pinecone_rag_v2.py api/index.py
```

### Step 2: Set Environment Variables in Vercel

In your Vercel dashboard:
1. Go to your project settings
2. Add environment variables:
   - `PINECONE_API_KEY`
   - `ANTHROPIC_API_KEY`
   - `OPENAI_API_KEY` (optional)
   - `PINECONE_INDEX_NAME` (defaults to "management-knowledge-v2")
   - `PINECONE_NAMESPACE` (defaults to "management-knowledge")

### Step 3: Deploy

```bash
# Commit and push (auto-deploys via GitHub integration)
git add .
git commit -m "🚀 Update to Pinecone API v2.0 (2025)"
git push origin master
```

## Technical Advantages of v2.0

### 🎯 **Integrated Embeddings**
- **No External Dependencies**: Embeddings handled by Pinecone
- **Cost Efficient**: No OpenAI embedding API costs
- **Faster Performance**: Integrated processing
- **Simplified Architecture**: Fewer moving parts

### 🔧 **Modern API Patterns**
- **CLI-Based Setup**: Industry standard approach
- **Namespace Support**: Better data isolation
- **Automatic Batching**: Optimized upload performance
- **Better Error Handling**: Improved reliability

### 📊 **Knowledge Quality**
- **Full Content Preserved**: All 816 chunks with rich metadata
- **Semantic Search**: Advanced similarity matching
- **Framework Filtering**: Category and source-based queries
- **Professional Responses**: Management consultant quality

## Troubleshooting v2.0

### Common Issues

1. **"pc command not found"**
   - Install CLI: `brew install pinecone-io/tap/pinecone`
   - Or download from GitHub releases

2. **"Index creation failed"**
   - Check API key: `pc auth configure --api-key $PINECONE_API_KEY`
   - Verify account has free tier quota

3. **"upsert_records not found"**
   - Update package: `pip install pinecone>=5.0.0`
   - Check import: `from pinecone import Pinecone`

4. **"Namespace not found"**
   - Check namespace exists in index stats
   - Re-run upload script if empty

### Performance Optimization

1. **Upload Speed**: Batch size optimized to 100 records
2. **Search Latency**: ~500ms with integrated embeddings
3. **Rate Limits**: 2-second delays between batches
4. **Memory Usage**: Efficient streaming processing

## Cost Estimation (v2.0)

### Free Tier Usage
- **Pinecone**: 2GB storage, 2M vectors (our 816 chunks ~50MB)
- **Embeddings**: Included in Pinecone (no OpenAI costs)
- **Anthropic**: Pay per API call for responses

### Production Usage
- **Pinecone**: ~$20-70/month for dedicated capacity
- **No Embedding Costs**: Included in Pinecone service
- **Anthropic**: ~$0.01-0.03 per AI response

Total estimated cost: **$20-100/month** for production use (reduced from v1.0).

## Migration from v1.0

If you used our previous implementation:

1. **Update Package**: `pip uninstall pinecone-client && pip install pinecone>=5.0.0`
2. **Install CLI**: Follow CLI installation steps above
3. **Create New Index**: Use CLI to create index with integrated embeddings
4. **Re-upload Data**: Use new `setup_pinecone_v2.py` script
5. **Update API**: Replace with `pinecone_rag_v2.py`

## Next Steps

1. ✅ Complete setup using `setup_pinecone_v2.py`
2. ✅ Test API endpoints locally
3. ✅ Deploy to Vercel with v2.0 API
4. ✅ Configure Custom GPT Actions
5. ✅ Run comprehensive testing with 40+ questions

The v2.0 implementation is more robust, cost-effective, and aligned with current Pinecone best practices! 🚀
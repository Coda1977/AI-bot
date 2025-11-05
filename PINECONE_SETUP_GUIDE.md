# Pinecone RAG API Setup Guide

## Overview
This guide helps you set up the Pinecone-based RAG API using the full-quality knowledge base (816 chunks, 320k+ words) with rich metadata.

## Prerequisites

### 1. Pinecone Account Setup
1. Go to [https://app.pinecone.io/](https://app.pinecone.io/)
2. Sign up for free account (generous free tier: 2GB storage, 2M vectors)
3. Create a new project or use default
4. Get your API key from the dashboard

### 2. API Keys Required
- **Pinecone API Key**: For vector database
- **OpenAI API Key**: For creating embeddings (text-embedding-ada-002)
- **Anthropic API Key**: For AI responses (Claude 3.5 Sonnet)

## Setup Steps

### Step 1: Configure Environment Variables

Create `.env` file with your API keys:

```bash
# Copy the example file
cp .env.pinecone.example .env

# Edit with your actual API keys
PINECONE_API_KEY=your_pinecone_api_key_here
OPENAI_API_KEY=your_openai_api_key_here
ANTHROPIC_API_KEY=your_anthropic_api_key_here
```

### Step 2: Install Dependencies

```bash
# Install Pinecone requirements
pip install -r requirements_pinecone.txt
```

### Step 3: Setup Pinecone Index and Upload Knowledge

```bash
# Run the setup script (creates index and uploads 816 chunks)
python setup_pinecone.py
```

This script will:
- Create a Pinecone index named "management-knowledge"
- Process all 816 knowledge chunks
- Create embeddings for each chunk using OpenAI
- Upload vectors with rich metadata to Pinecone
- Verify the upload was successful

### Step 4: Test Locally

```bash
# Start the API server
python api/pinecone_rag.py
```

Test endpoints:
- Health check: http://localhost:8000/api/health
- Search: POST to http://localhost:8000/api/search
- Ask: POST to http://localhost:8000/api/ask

## Deployment to Vercel

### Step 1: Update requirements.txt for Vercel

```bash
# Copy Pinecone requirements to main requirements file
cp requirements_pinecone.txt requirements.txt
```

### Step 2: Set Environment Variables in Vercel

In your Vercel dashboard:
1. Go to your project settings
2. Add environment variables:
   - `PINECONE_API_KEY`
   - `OPENAI_API_KEY`
   - `ANTHROPIC_API_KEY`
   - `PINECONE_INDEX_NAME` (optional, defaults to "management-knowledge")

### Step 3: Deploy

```bash
# Commit and push (auto-deploys via GitHub integration)
git add .
git commit -m "🚀 Add Pinecone-based RAG API with full knowledge base"
git push origin master
```

## API Endpoints

### Health Check
```
GET /api/health
```
Returns system status and configuration.

### Search Knowledge Base
```
POST /api/search
{
  "query": "How do I give difficult feedback?",
  "top_k": 5,
  "filter": {"category": "Feedback"}  // optional
}
```

### Ask Question (AI Response)
```
POST /api/ask
{
  "question": "What's the best way to delegate effectively?",
  "top_k": 5,
  "ai_provider": "anthropic"  // optional
}
```

## Knowledge Base Details

### Content Quality
- **816 semantic chunks** from 37 management resources
- **320,634 total words** (full content, no compression)
- **Rich metadata** preserved:
  - Source file and path
  - Framework identification
  - Category and section
  - Keywords and language
  - Word/character counts

### Search Capabilities
- **Semantic search** using OpenAI embeddings
- **Metadata filtering** by source, framework, category
- **Relevance scoring** with confidence levels
- **Multi-language support** (English/Hebrew detection)

### AI Response Quality
- **Professional consulting tone**
- **Framework-specific guidance**
- **Source citations** from knowledge base
- **Actionable recommendations**
- **Multi-provider fallback** (Anthropic → OpenAI)

## Troubleshooting

### Common Issues

1. **"PINECONE_API_KEY not found"**
   - Verify API key is set in environment variables
   - Check Pinecone dashboard for correct API key

2. **"Index not found"**
   - Run `python setup_pinecone.py` to create index
   - Check index name matches `PINECONE_INDEX_NAME`

3. **"No vectors found"**
   - Knowledge base upload may have failed
   - Re-run setup script to upload chunks

4. **"Embedding creation failed"**
   - Verify OpenAI API key is valid
   - Check OpenAI account has sufficient credits

### Performance Optimization

1. **Response Time**: ~2-3 seconds (embedding + search + AI)
2. **Batch Size**: 100 chunks per upload batch
3. **Top-K Results**: Default 5, adjustable up to 20
4. **Caching**: Clients cached as singletons

## Cost Estimation

### Free Tier Usage
- **Pinecone**: 2GB storage (our 816 chunks ~50MB)
- **OpenAI**: ~$2-5 for initial embedding creation
- **Anthropic**: Pay per API call for responses

### Production Usage
- **Pinecone**: ~$20-70/month for dedicated index
- **OpenAI**: ~$0.0001 per search embedding
- **Anthropic**: ~$0.01-0.03 per AI response

Total estimated cost: **$30-100/month** for production use.

## Next Steps

1. ✅ Test API endpoints locally
2. ✅ Deploy to Vercel
3. ✅ Configure Custom GPT Actions
4. ✅ Run comprehensive testing with 40+ questions
5. ✅ Validate response quality and accuracy

The Pinecone approach gives you enterprise-grade vector search with full knowledge quality - perfect for validating your RAG system before building the Docker enterprise solution!
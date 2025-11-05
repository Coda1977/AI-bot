# Management Knowledge RAG API

A FastAPI service that provides semantic search and AI-powered responses using a comprehensive management knowledge base.

## Features

- **Semantic Search**: Find relevant management content using natural language queries
- **AI-Powered Responses**: Get comprehensive answers with source citations
- **Multi-Provider AI**: Supports both Anthropic Claude and OpenAI GPT models
- **ChromaDB Integration**: Fast vector search across 800+ knowledge chunks
- **Custom GPT Actions**: Ready for integration with ChatGPT custom actions
- **RESTful API**: Clean, documented endpoints

## Quick Start

### Local Development

1. **Install Dependencies**:
   ```bash
   pip install -r requirements_rag.txt
   ```

2. **Configure Environment**:
   ```bash
   cp .env.rag.example .env
   # Edit .env with your API keys
   ```

3. **Run the API**:
   ```bash
   python rag_api.py
   ```

4. **Test the API**:
   ```bash
   python test_rag_api.py
   ```

### Cloud Deployment (Railway)

1. **Connect to Railway**:
   ```bash
   railway login
   railway init
   ```

2. **Set Environment Variables**:
   ```bash
   railway variables set ANTHROPIC_API_KEY=your_key_here
   railway variables set OPENAI_API_KEY=your_key_here
   ```

3. **Deploy**:
   ```bash
   railway up
   ```

## API Endpoints

### Health Check
```http
GET /health
```

Returns service status and configuration.

### Search Knowledge Base
```http
POST /search
```

**Request Body**:
```json
{
  "query": "How to give feedback to underperforming employees",
  "domain": "feedback",
  "detail_level": "detailed",
  "max_results": 5
}
```

**Response**:
```json
{
  "results": [
    {
      "content": "Framework content...",
      "source_file": "Giving Feedback.pptx",
      "relevance_score": 0.95,
      "metadata": {...}
    }
  ],
  "query": "How to give feedback...",
  "total_results": 5
}
```

### Ask Question (AI-Powered)
```http
POST /ask
```

**Request Body**:
```json
{
  "query": "How should I handle a team member who constantly interrupts others?",
  "detail_level": "detailed",
  "context_size": 5
}
```

**Response**:
```json
{
  "answer": "Based on the management frameworks in your knowledge base...",
  "sources": [...],
  "query": "How should I handle...",
  "ai_provider": "anthropic"
}
```

## Custom GPT Integration

### 1. Deploy the API
Deploy to Railway or another cloud provider to get a public HTTPS endpoint.

### 2. Configure Custom GPT Action
1. Go to ChatGPT → Create Custom GPT
2. In Actions section, import the OpenAPI schema from `openapi_schema.json`
3. Update the server URL in the schema to your deployed API endpoint

### 3. Add Instructions
```
You are a management consultant with access to comprehensive training materials through the Management Knowledge API.

For management questions:
1. Use the askQuestion action to get AI-powered responses with source citations
2. For quick searches, use the searchKnowledge action
3. Always provide specific, actionable advice
4. Include framework references and next steps

Example usage:
- "How do I give difficult feedback?" → Use askQuestion action
- "Show me delegation frameworks" → Use searchKnowledge action
```

### 4. Test
Use the provided test questions to validate the integration works correctly.

## Knowledge Base

The API includes 800+ processed chunks from comprehensive management materials:

- **Feedback & Communication**: SBI frameworks, difficult conversations, radical candor
- **Leadership**: High output management, strategic thinking, executive presence
- **Coaching**: Performance coaching, development planning, motivation systems
- **Team Management**: Team building, conflict resolution, psychological safety
- **Delegation**: Authority levels, decision matrices, accountability systems
- **Performance**: Goal setting, performance conversations, improvement planning

## Configuration

### Required Environment Variables
- `ANTHROPIC_API_KEY` or `OPENAI_API_KEY` (at least one)

### Optional Environment Variables
- `PREFERRED_AI_PROVIDER`: Choose between "anthropic" or "openai"
- `PORT`: Port for local development (default: 8000)
- `LOG_LEVEL`: Logging level (default: INFO)

## Testing

### Automated Tests
```bash
python test_rag_api.py
```

### Manual Testing
```bash
# Health check
curl http://localhost:8000/health

# Search
curl -X POST http://localhost:8000/search \
  -H "Content-Type: application/json" \
  -d '{"query": "feedback frameworks", "max_results": 3}'

# Ask question
curl -X POST http://localhost:8000/ask \
  -H "Content-Type: application/json" \
  -d '{"query": "How to delegate effectively?"}'
```

### Test Questions
Use these management scenarios to validate the API:

1. "How do I give feedback to an underperforming team member?"
2. "What's the best way to delegate important tasks?"
3. "How should I handle conflict between team members?"
4. "What frameworks help with performance conversations?"
5. "How do I motivate a disengaged employee?"

## Architecture

```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   Custom GPT    │───▶│   FastAPI RAG    │───▶│   ChromaDB      │
│   (ChatGPT)     │    │   Service        │    │   Knowledge     │
└─────────────────┘    └──────────────────┘    └─────────────────┘
                                │
                                ▼
                       ┌──────────────────┐
                       │  AI Providers    │
                       │  (Claude/GPT-4)  │
                       └──────────────────┘
```

## Performance

- **Search Latency**: ~100-300ms for semantic search
- **AI Response Time**: 1-3 seconds (depending on provider)
- **Knowledge Base Size**: 800+ chunks, 320k+ words
- **Concurrent Requests**: Supports multiple simultaneous queries

## Security

- API keys required for AI providers
- CORS configured for ChatGPT domains
- No persistent user data storage
- All processing happens on configured cloud infrastructure

## Troubleshooting

### Common Issues

1. **"Knowledge base not found"**
   - Ensure `output/chromadb_data/chunks_data.json` exists
   - Run the ingestion process first

2. **"AI service unavailable"**
   - Check API keys are set correctly
   - Verify API key has sufficient credits

3. **"No results found"**
   - Try broader search terms
   - Check if knowledge base loaded correctly

### Logs
```bash
# Check application logs
railway logs

# Local development logs
python rag_api.py  # Logs printed to console
```

## Next Steps

After validating the RAG API:

1. **Test with Custom GPT**: Validate the ChatGPT Actions integration
2. **Optimize Performance**: Tune search parameters and AI prompts
3. **Add Analytics**: Track usage patterns and popular queries
4. **Docker Packaging**: Create containerized version for enterprise deployment
5. **Slack Bot Integration**: Use same RAG backend with Slack interface

## Support

For issues or questions:
- Check the logs for detailed error messages
- Verify environment variables are set correctly
- Test individual endpoints to isolate issues
- Review the OpenAPI schema for correct request formats
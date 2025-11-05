# Vercel Deployment Guide

## Quick Deployment Steps

### 1. Initialize Vercel Project
```bash
cd "/home/yonat/AI bot"
npx vercel login
npx vercel init
```

### 2. Set Environment Variables
```bash
vercel env add ANTHROPIC_API_KEY
# Paste your API key when prompted

# Optional: Add OpenAI as backup
vercel env add OPENAI_API_KEY
```

### 3. Deploy
```bash
vercel --prod
```

## Files Created for Vercel

- ✅ `api/index.py` - Vercel-optimized FastAPI app
- ✅ `vercel.json` - Vercel configuration
- ✅ `requirements.txt` - Python dependencies
- ✅ `chunks_data.json` - Knowledge base (copied to root)
- ✅ `openapi_schema.json` - Updated for Vercel URLs

## Vercel-Specific Optimizations

### Serverless Adaptations
- **In-memory ChromaDB**: No persistent files in serverless
- **Singleton pattern**: Reuse clients across invocations
- **Smaller batch sizes**: Optimized for serverless constraints
- **Error handling**: Graceful fallbacks for cold starts

### URL Structure
- **Root endpoint**: `https://your-app.vercel.app/api`
- **Health check**: `https://your-app.vercel.app/api/health`
- **Search**: `https://your-app.vercel.app/api/search`
- **Ask**: `https://your-app.vercel.app/api/ask`

## After Deployment

### 1. Test Your API
```bash
# Replace with your actual Vercel URL
curl https://your-app.vercel.app/api/health
```

### 2. Update OpenAPI Schema
1. Open `openapi_schema.json`
2. Replace `https://your-rag-api.vercel.app` with your actual Vercel URL
3. Save the file

### 3. Configure Custom GPT
1. Go to ChatGPT → Create Custom GPT
2. In Actions section, import the updated `openapi_schema.json`
3. Test with: "How do I give difficult feedback?"

## Troubleshooting

### Common Issues

**"Function timeout"**
- Vercel free tier has 10-second timeout
- Upgrade to Pro for 60-second timeout if needed

**"Module not found"**
- Check `requirements.txt` is in root directory
- Verify all dependencies are listed

**"Knowledge base not found"**
- Ensure `chunks_data.json` is in root directory (not in subdirectory)
- Check file size is under Vercel limits

### Monitoring
- Check function logs in Vercel dashboard
- Monitor response times and error rates
- Set up alerts for failures

## Costs

### Vercel Free Tier
- ✅ 100GB bandwidth per month
- ✅ 100 serverless function executions per day
- ✅ Perfect for testing and validation

### Vercel Pro ($20/month)
- ✅ 1TB bandwidth
- ✅ Unlimited function executions
- ✅ 60-second function timeout
- ✅ Custom domains

## Next Steps

1. **Deploy to Vercel** using steps above
2. **Test the API** with health check and sample queries
3. **Configure Custom GPT** with your Vercel URL
4. **Validate with test questions** to ensure quality
5. **Share with beta users** for feedback

Your RAG API will be live at `https://your-project-name.vercel.app/api`!
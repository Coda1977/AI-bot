# Manager AI Assistant - Smart Materials Ingestion System

A powerful system for processing management frameworks and materials into AI-ready formats for Custom GPTs, Slack bots, and other AI assistant platforms.

## 🚀 Quick Start

### 1. Installation

```bash
# Clone or download this project
cd "AI bot"

# Install dependencies
pip install -r requirements.txt
```

### 2. Configuration

```bash
# Copy environment template
cp .env.example .env

# Edit .env with your API key
nano .env
```

Required: Add your AI provider API key to `.env`:
```bash
# For Anthropic Claude (recommended)
AI_PROVIDER=anthropic
ANTHROPIC_API_KEY=sk-ant-your-key-here

# OR for OpenAI
AI_PROVIDER=openai
OPENAI_API_KEY=sk-your-key-here

# OR for Google Gemini
AI_PROVIDER=gemini
GOOGLE_API_KEY=your-google-api-key
```

### 3. Add Your Materials

Place your management materials in the `materials/` directory:

```
materials/
├── performance_framework.docx
├── leadership_guide.pdf
├── communication_strategies.pptx
├── conflict_resolution.md
└── delegation_framework.txt
```

**Supported Formats:**
- Word documents (`.docx`)
- PDF files (`.pdf`)
- PowerPoint presentations (`.pptx`)
- Markdown files (`.md`)
- Text files (`.txt`)

### 4. Run Smart Ingestion

```bash
# Check what materials are available
python cli.py check-materials

# Run the ingestion process
python cli.py ingest

# View results
ls output/
```

## 📋 What It Does

The smart ingestion system:

1. **📖 Extracts text** from Word docs, PDFs, PowerPoints, and other formats
2. **🤖 AI-powered chunking** - Uses Claude/GPT to intelligently break content into 300-500 word chunks
3. **🏷️ Auto-generates metadata** - Framework names, categories, keywords, language detection
4. **📤 Multi-format output**:
   - **Custom GPT files** - Individual markdown files ready for ChatGPT upload
   - **ChromaDB data** - Structured JSON for vector database (future Slack bot)

## 🎯 Output Formats

### Custom GPT Package
Perfect for creating Custom GPTs in ChatGPT:
```
output/custom_gpt_files/
├── chunk_001_Performance_Framework_Goal_Setting.md
├── chunk_002_Performance_Framework_Feedback.md
├── chunk_003_Leadership_Guide_Team_Building.md
└── ... (20-50 optimized files)
```

Each file contains:
- Proper headers and formatting
- Framework name and section
- Category and keywords
- Standalone content with context

### ChromaDB Data
For building Slack bots and advanced AI systems:
```
output/chromadb_data/
└── chunks_data.json  # Structured data ready for vector search
```

## 🔧 Advanced Usage

### Custom Output Formats
```bash
# Only generate Custom GPT files
python cli.py ingest --formats custom_gpt

# Only generate ChromaDB data
python cli.py ingest --formats chromadb

# Both (default)
python cli.py ingest --formats custom_gpt --formats chromadb
```

### Different AI Providers
```bash
# Use OpenAI for chunking
python cli.py ingest --ai-provider openai

# Use Gemini for chunking
python cli.py ingest --ai-provider gemini
```

### Custom Directories
```bash
# Custom materials and output directories
python cli.py ingest --materials-dir /path/to/materials --output-dir /path/to/output
```

## 📊 Quality Analysis

The system automatically analyzes chunk quality:

- **Word count validation** (300-500 words target)
- **Context header verification**
- **Framework identification accuracy**
- **Language detection**
- **Metadata completeness**

View the full report:
```bash
python cli.py report output/ingestion_report.json
```

## 🎮 Next Steps: Custom GPT Setup

Once ingestion is complete:

1. **Go to ChatGPT** → Create Custom GPT
2. **Upload all files** from `output/custom_gpt_files/`
3. **Set system prompt** (see `system_prompts/` directory)
4. **Test with management questions**

Example questions to test:
- "How do I give negative feedback to an underperforming employee?"
- "Two team members are in conflict, what should I do?"
- "What's the best way to delegate tasks?"

## 🔍 Troubleshooting

### Common Issues

**"No API key found"**
- Check your `.env` file has the correct API key
- Make sure the key starts with the right prefix (sk-ant-, sk-, etc.)

**"No supported files found"**
- Check materials are in `materials/` directory
- Verify file formats (.docx, .pdf, .pptx, .md, .txt)

**"AI chunking failed"**
- Check your API key has sufficient credits
- Try a different AI provider
- Check internet connection

**"Short/long chunks"**
- This is normal - the system will flag but still process
- Review the quality report for optimization suggestions

### Getting Help

1. Check the `ingestion_report.json` for detailed error messages
2. Run with verbose logging: `python cli.py --log-level DEBUG ingest`
3. Ensure your materials contain substantial management content

## 📁 Project Structure

```
AI bot/
├── src/
│   ├── document_processor.py    # Extract text from files
│   ├── ai_client.py            # Multi-provider AI interface
│   ├── smart_ingestion.py      # Main chunking logic
│   └── config.py               # Configuration management
├── materials/                  # Your source documents
├── output/                     # Generated outputs
│   ├── custom_gpt_files/      # Ready for Custom GPT
│   ├── chromadb_data/         # Ready for vector DB
│   └── ingestion_report.json   # Quality analysis
├── cli.py                      # Command line interface
├── requirements.txt            # Dependencies
├── .env.example               # Configuration template
└── README.md                  # This file
```

## 🌟 Features

- ✅ **Multi-format support** - Word, PDF, PowerPoint, Markdown, Text
- ✅ **AI-powered chunking** - Intelligent content breakup
- ✅ **Multi-language** - Hebrew and English support
- ✅ **Quality analysis** - Automatic validation and reporting
- ✅ **Multiple outputs** - Custom GPT + ChromaDB ready
- ✅ **Flexible configuration** - Multiple AI providers
- ✅ **Rich CLI** - Beautiful progress bars and reports

## 🚀 What's Next?

This smart ingestion system is Phase 1 of the Manager AI Assistant platform:

- **Phase 2**: Custom GPT testing and validation
- **Phase 3**: Slack bot development
- **Phase 4**: Multi-platform deployment (Teams, Discord, etc.)

The materials you process here will work across all these platforms! 🎯# Updated Wed Nov  5 17:52:05 IST 2025

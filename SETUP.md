# Setup Guide - Manager AI Assistant Smart Ingestion

Complete step-by-step guide to get the smart ingestion system running.

## Prerequisites

- Python 3.8+ installed
- Internet connection for AI API calls
- API key from one of: Anthropic Claude, OpenAI, or Google Gemini

## Step 1: Install Python Dependencies

### Option A: User Installation (Recommended)
```bash
cd "AI bot"
python3 -m pip install -r requirements.txt --user
```

### Option B: Virtual Environment (Advanced)
```bash
cd "AI bot"
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### Option C: System Installation (if you have admin rights)
```bash
cd "AI bot"
sudo apt install python3-pip python3-venv  # Ubuntu/Debian
pip3 install -r requirements.txt
```

## Step 2: Configure API Key

### 2.1 Copy Environment Template
```bash
cp .env.example .env
```

### 2.2 Edit Configuration
Open `.env` in a text editor and add your API key:

**For Anthropic Claude (Recommended):**
```bash
AI_PROVIDER=anthropic
ANTHROPIC_API_KEY=sk-ant-your-actual-key-here
```

**For OpenAI GPT:**
```bash
AI_PROVIDER=openai
OPENAI_API_KEY=sk-your-actual-key-here
```

**For Google Gemini:**
```bash
AI_PROVIDER=gemini
GOOGLE_API_KEY=your-actual-google-key-here
```

### 2.3 Get API Keys

**Anthropic Claude:**
1. Go to https://console.anthropic.com/
2. Sign up/login
3. Go to "API Keys"
4. Create new key
5. Copy key (starts with `sk-ant-`)

**OpenAI:**
1. Go to https://platform.openai.com/api-keys
2. Sign up/login
3. Create new secret key
4. Copy key (starts with `sk-`)

**Google Gemini:**
1. Go to https://aistudio.google.com/app/apikey
2. Sign up/login
3. Create API key
4. Copy key

## Step 3: Add Your Materials

### 3.1 Prepare Your Materials
Put your management frameworks, guides, and documents in the `materials/` folder:

```
materials/
├── performance_management_framework.docx
├── leadership_guide.pdf
├── communication_strategies.pptx
├── conflict_resolution_guide.md
├── delegation_framework.txt
└── team_building_exercises.pdf
```

### 3.2 Supported File Formats
- ✅ Word documents (`.docx`)
- ✅ PDF files (`.pdf`)
- ✅ PowerPoint presentations (`.pptx`)
- ✅ Markdown files (`.md`)
- ✅ Text files (`.txt`)

### 3.3 Material Quality Tips
**Good materials include:**
- Specific frameworks and methodologies
- Step-by-step processes
- Real examples and scenarios
- Clear section headings
- Actionable guidance for managers

**Avoid:**
- Generic motivational content
- Very short documents (<100 words)
- Images-only content (PDFs with no text)
- Highly technical non-management content

## Step 4: Test the System

### 4.1 Check Everything is Working
```bash
python3 simple_test.py
```

Should show all green checkmarks ✅.

### 4.2 Check Your Materials
```bash
python3 cli.py check-materials
```

This will show all the files found and their sizes.

### 4.3 Test Basic Functionality (Optional)
If you have dependencies installed:
```bash
python3 test_basic.py
```

## Step 5: Run Smart Ingestion

### 5.1 Full Ingestion
```bash
python3 cli.py ingest
```

This will:
1. Extract text from all your documents
2. Use AI to chunk them intelligently
3. Generate metadata and keywords
4. Create Custom GPT files
5. Create ChromaDB data
6. Generate quality report

### 5.2 Monitor Progress
You'll see progress like:
```
🚀 Starting smart ingestion...
📁 Materials: materials
📤 Output: output
🤖 AI Provider: anthropic
📋 Formats: chromadb, custom_gpt

Processing materials... ⣾
```

### 5.3 Review Results
After completion, check:
- `output/custom_gpt_files/` - Ready for Custom GPT upload
- `output/chromadb_data/` - Ready for Slack bot
- `output/ingestion_report.json` - Quality analysis

## Step 6: Create Your Custom GPT

### 6.1 Go to ChatGPT
1. Visit https://chat.openai.com/
2. Click your profile → "My GPTs"
3. Click "Create a GPT"

### 6.2 Upload Your Materials
1. In the "Configure" tab
2. Click "Upload files" in the Knowledge section
3. Upload ALL files from `output/custom_gpt_files/`
4. This might be 20-50 files - upload them all

### 6.3 Set Instructions
Copy the content from `system_prompts/custom_gpt_prompt.txt` and paste it in the "Instructions" field.

### 6.4 Configure Basic Info
- **Name:** "[Your Company] Manager Assistant"
- **Description:** "Expert management advisor with proprietary frameworks"
- **Conversation starters:** Copy from `system_prompts/test_questions.txt`

### 6.5 Test Your Custom GPT
Try these questions:
- "How do I give negative feedback to an underperforming employee?"
- "Two team members are in conflict, what should I do?"

Check that it:
- ✅ Cites your frameworks correctly
- ✅ Gives specific, actionable advice
- ✅ Uses the proper response format

## Troubleshooting

### "No module named 'docx'"
```bash
python3 -m pip install python-docx --user
```

### "API key not found"
Check that:
- You copied `.env.example` to `.env`
- Your API key is correct (no extra spaces)
- The key starts with the right prefix (sk-ant-, sk-, etc.)

### "No supported files found"
Check that:
- Files are in `materials/` directory
- Files have supported extensions (.docx, .pdf, .pptx, .md, .txt)
- Files are not empty

### "AI chunking failed"
Check:
- Your API key works and has credits
- Internet connection is stable
- Try a different AI provider in `.env`

### Permission Errors
Try:
```bash
python3 -m pip install --user -r requirements.txt
```

### Custom GPT Upload Issues
- Upload files one by one if bulk upload fails
- Make sure files are under ChatGPT's file size limits
- Check file names don't have special characters

## Advanced Configuration

### Different Output Formats
```bash
# Only Custom GPT files
python3 cli.py ingest --formats custom_gpt

# Only ChromaDB data
python3 cli.py ingest --formats chromadb
```

### Different AI Provider
```bash
# Use OpenAI for chunking
python3 cli.py ingest --ai-provider openai
```

### Custom Directories
```bash
python3 cli.py ingest --materials-dir /path/to/docs --output-dir /path/to/output
```

### View Detailed Report
```bash
python3 cli.py report output/ingestion_report.json
```

## Success Checklist

Before considering setup complete:

- [ ] Dependencies installed without errors
- [ ] API key configured and working
- [ ] Materials uploaded (at least 3-5 substantial documents)
- [ ] Smart ingestion runs successfully
- [ ] Quality report shows good chunk metrics
- [ ] Custom GPT created and uploaded
- [ ] Test questions work properly
- [ ] Framework citations are accurate

## Getting Help

### Check Logs
Enable detailed logging:
```bash
python3 cli.py --log-level DEBUG ingest
```

### Common Issues
1. **Import errors** → Install dependencies
2. **API errors** → Check key and credits
3. **File errors** → Check materials format and content
4. **Permission errors** → Use `--user` flag with pip

### Support Checklist
If you need help, provide:
- Output of `python3 simple_test.py`
- Content of your `.env` file (hide the actual API key)
- Error messages from ingestion
- Sample of your materials (file names and types)

The system is designed to work out-of-the-box once dependencies and API keys are configured correctly. Most issues are related to Python environment setup or API key configuration.
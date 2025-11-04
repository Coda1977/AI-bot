#!/usr/bin/env python3
"""
Basic test to verify the smart ingestion system works
"""

import os
from pathlib import Path
from src.document_processor import DocumentProcessor

def test_document_processor():
    """Test that document processor can read our sample materials"""
    print("🧪 Testing Document Processor...")

    processor = DocumentProcessor()
    materials_dir = Path("materials")

    if not materials_dir.exists():
        print("❌ Materials directory not found")
        return False

    # Test processing sample materials
    docs = processor.process_directory(materials_dir)

    if not docs:
        print("❌ No documents processed")
        return False

    print(f"✅ Processed {len(docs)} documents")

    for doc in docs:
        if doc['processing_status'] == 'success':
            print(f"  ✅ {doc['filename']}: {doc['word_count']} words")
        else:
            print(f"  ❌ {doc['filename']}: {doc.get('error_message', 'Unknown error')}")

    # Get summary
    summary = processor.get_processing_summary(docs)
    print(f"\n📊 Summary:")
    print(f"  • Total files: {summary['total_files']}")
    print(f"  • Successful: {summary['successful']}")
    print(f"  • Failed: {summary['failed']}")
    print(f"  • Total words: {summary['total_words']:,}")

    return summary['successful'] > 0

def check_dependencies():
    """Check if required dependencies are available"""
    print("🔍 Checking dependencies...")

    try:
        import anthropic
        print("  ✅ anthropic")
    except ImportError:
        print("  ❌ anthropic (pip install anthropic)")
        return False

    try:
        import openai
        print("  ✅ openai")
    except ImportError:
        print("  ❌ openai (pip install openai)")
        return False

    try:
        import google.generativeai
        print("  ✅ google-generativeai")
    except ImportError:
        print("  ❌ google-generativeai (pip install google-generativeai)")
        return False

    try:
        from docx import Document
        print("  ✅ python-docx")
    except ImportError:
        print("  ❌ python-docx (pip install python-docx)")
        return False

    try:
        import PyPDF2
        print("  ✅ PyPDF2")
    except ImportError:
        print("  ❌ PyPDF2 (pip install PyPDF2)")
        return False

    try:
        from pptx import Presentation
        print("  ✅ python-pptx")
    except ImportError:
        print("  ❌ python-pptx (pip install python-pptx)")
        return False

    return True

def check_api_keys():
    """Check if API keys are available"""
    print("🔑 Checking API keys...")

    anthropic_key = os.getenv('ANTHROPIC_API_KEY')
    openai_key = os.getenv('OPENAI_API_KEY')
    google_key = os.getenv('GOOGLE_API_KEY')

    if anthropic_key:
        print("  ✅ ANTHROPIC_API_KEY found")
        return True
    elif openai_key:
        print("  ✅ OPENAI_API_KEY found")
        return True
    elif google_key:
        print("  ✅ GOOGLE_API_KEY found")
        return True
    else:
        print("  ❌ No API keys found")
        print("  💡 Create a .env file with one of:")
        print("     ANTHROPIC_API_KEY=sk-ant-your-key")
        print("     OPENAI_API_KEY=sk-your-key")
        print("     GOOGLE_API_KEY=your-google-key")
        return False

if __name__ == "__main__":
    print("🚀 Smart Ingestion System - Basic Test\n")

    # Check dependencies
    if not check_dependencies():
        print("\n❌ Missing dependencies. Run: pip install -r requirements.txt")
        exit(1)

    # Check API keys
    has_api_key = check_api_keys()

    # Test document processing
    if test_document_processor():
        print("\n✅ Document processor working correctly!")

        if has_api_key:
            print("\n🎯 Ready to run smart ingestion!")
            print("   Next steps:")
            print("   1. Add your materials to the materials/ directory")
            print("   2. Run: python cli.py ingest")
        else:
            print("\n⚠️  Add an API key to .env to run full smart ingestion")
    else:
        print("\n❌ Document processor test failed")

    print("\n" + "="*50)
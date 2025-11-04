"""
Smart Materials Ingestion System
AI-powered document chunking and optimization for management frameworks
"""

import os
import json
from pathlib import Path
from typing import Dict, List, Optional, Any
import logging
from datetime import datetime

from .document_processor import DocumentProcessor
from .ai_client import AIClientFactory, AIClient

logger = logging.getLogger(__name__)

class SmartMaterialsIngestion:
    """
    AI-powered system for chunking and optimizing management materials
    Outputs: ChromaDB-ready data + Custom GPT markdown files
    """

    def __init__(
        self,
        ai_provider: str = "anthropic",
        api_key: Optional[str] = None,
        output_formats: List[str] = None
    ):
        """
        Initialize the smart ingestion system

        Args:
            ai_provider: 'anthropic', 'openai', or 'gemini'
            api_key: API key for the AI provider
            output_formats: List of formats to output ['chromadb', 'custom_gpt']
        """
        self.ai_provider = ai_provider
        self.output_formats = output_formats or ['chromadb', 'custom_gpt']

        # Initialize AI client
        if not api_key:
            api_key = self._get_api_key_from_env(ai_provider)

        self.ai_client = AIClientFactory.create_client(ai_provider, api_key)
        self.document_processor = DocumentProcessor()

        # Configuration
        self.chunk_size_range = (300, 500)  # Target word count per chunk
        self.max_chunks_per_doc = 20  # Prevent overly long documents from creating too many chunks

    def _get_api_key_from_env(self, provider: str) -> str:
        """Get API key from environment variables"""
        key_map = {
            'anthropic': 'ANTHROPIC_API_KEY',
            'openai': 'OPENAI_API_KEY',
            'gemini': 'GOOGLE_API_KEY'
        }

        env_var = key_map.get(provider)
        if not env_var:
            raise ValueError(f"Unknown provider: {provider}")

        api_key = os.getenv(env_var)
        if not api_key:
            raise ValueError(f"API key not found in environment: {env_var}")

        return api_key

    def process_materials_directory(self, materials_path: Path, output_dir: Path) -> Dict:
        """
        Process all materials in a directory and generate optimized outputs

        Args:
            materials_path: Path to directory containing source materials
            output_dir: Path to directory for outputs

        Returns:
            Processing report with metrics and quality analysis
        """
        logger.info(f"Starting smart ingestion from: {materials_path}")

        # Create output directories
        output_dir.mkdir(exist_ok=True)
        if 'chromadb' in self.output_formats:
            (output_dir / 'chromadb_data').mkdir(exist_ok=True)
        if 'custom_gpt' in self.output_formats:
            (output_dir / 'custom_gpt_files').mkdir(exist_ok=True)

        # Step 1: Extract text from all documents
        logger.info("Step 1: Extracting text from documents...")
        raw_documents = self.document_processor.process_directory(materials_path)

        processing_summary = self.document_processor.get_processing_summary(raw_documents)
        logger.info(f"Processed {processing_summary['total_files']} files, {processing_summary['successful']} successful")

        # Step 2: AI-powered chunking and optimization
        logger.info("Step 2: AI-powered chunking and optimization...")
        all_chunks = []
        failed_documents = []

        for doc in raw_documents:
            if doc['processing_status'] != 'success':
                failed_documents.append(doc)
                continue

            try:
                chunks = self._intelligent_chunking(doc)
                all_chunks.extend(chunks)
                logger.info(f"Generated {len(chunks)} chunks from {doc['filename']}")
            except Exception as e:
                logger.error(f"Failed to chunk {doc['filename']}: {e}")
                failed_documents.append({**doc, 'chunking_error': str(e)})

        # Step 3: Quality analysis
        logger.info("Step 3: Analyzing chunk quality...")
        quality_metrics = self._analyze_chunk_quality(all_chunks)

        # Step 4: Export to formats
        logger.info("Step 4: Exporting to output formats...")
        export_results = {}

        if 'chromadb' in self.output_formats:
            export_results['chromadb'] = self._export_to_chromadb_format(all_chunks, output_dir / 'chromadb_data')

        if 'custom_gpt' in self.output_formats:
            export_results['custom_gpt'] = self._export_to_custom_gpt_format(all_chunks, output_dir / 'custom_gpt_files')

        # Step 5: Generate comprehensive report
        report = {
            'ingestion_date': datetime.now().isoformat(),
            'ai_provider': self.ai_provider,
            'source_directory': str(materials_path),
            'output_directory': str(output_dir),
            'processing_summary': processing_summary,
            'chunking_results': {
                'total_chunks_created': len(all_chunks),
                'average_chunk_size_words': sum(c['word_count'] for c in all_chunks) / len(all_chunks) if all_chunks else 0,
                'successful_documents': len(raw_documents) - len(failed_documents),
                'failed_documents': len(failed_documents)
            },
            'quality_metrics': quality_metrics,
            'export_results': export_results,
            'failed_documents': failed_documents
        }

        # Save report
        report_path = output_dir / 'ingestion_report.json'
        with open(report_path, 'w', encoding='utf-8') as f:
            json.dump(report, f, indent=2, ensure_ascii=False)

        logger.info(f"Smart ingestion complete! Report saved to: {report_path}")
        return report

    def _intelligent_chunking(self, document: Dict) -> List[Dict]:
        """
        Use AI to intelligently chunk a document

        Args:
            document: Document dictionary from document processor

        Returns:
            List of chunk dictionaries with content and metadata
        """
        content = document['content']
        filename = document['filename']

        # Skip very short documents
        if document['word_count'] < 100:
            logger.warning(f"Skipping short document: {filename} ({document['word_count']} words)")
            return []

        # Prepare AI prompt for chunking
        chunking_prompt = self._build_chunking_prompt(content, filename)

        try:
            # Get AI response
            ai_response = self.ai_client.generate_text(chunking_prompt, max_tokens=8000)

            # Parse AI response
            chunks_data = self._parse_chunking_response(ai_response, document)

            return chunks_data

        except Exception as e:
            logger.error(f"AI chunking failed for {filename}: {e}")
            # Fallback to simple chunking
            return self._fallback_chunking(document)

    def _build_chunking_prompt(self, content: str, filename: str) -> str:
        """Build the AI prompt for intelligent document chunking"""
        return f"""You are an expert at organizing management knowledge for AI retrieval systems.

Your task: Analyze this management document and break it into optimal chunks for semantic search.

DOCUMENT: {filename}
CONTENT:
{content}

REQUIREMENTS:
1. Create 3-8 chunks of 300-500 words each
2. Each chunk must be standalone with context header
3. Generate rich metadata for each chunk
4. Focus on management frameworks, processes, and actionable guidance

OUTPUT FORMAT (JSON):
{{
    "document_analysis": {{
        "main_framework": "Name of the primary framework/concept",
        "category": "Performance Management | Leadership | Communication | etc.",
        "key_topics": ["topic1", "topic2", "topic3"]
    }},
    "chunks": [
        {{
            "chunk_id": "unique_id_1",
            "content": "CONTEXT HEADER: [Framework Name - Section]\n\nChunk content here...",
            "metadata": {{
                "framework": "Framework name",
                "category": "Performance Management",
                "section": "Specific section name",
                "keywords": ["keyword1", "keyword2", "keyword3"],
                "language": "english" or "hebrew",
                "chunk_type": "framework_explanation | steps | examples | guidelines"
            }}
        }}
    ]
}}

CRITICAL:
- Each chunk must include a context header
- Content must be actionable for managers
- Keywords should be specific management terms
- Detect language (english/hebrew) automatically
- If document is bilingual, create separate chunks for each language"""

    def _parse_chunking_response(self, ai_response: str, original_doc: Dict) -> List[Dict]:
        """Parse AI response and convert to chunk format"""
        try:
            # Try to extract JSON from AI response
            import re
            json_match = re.search(r'\{.*\}', ai_response, re.DOTALL)
            if not json_match:
                raise ValueError("No JSON found in AI response")

            response_data = json.loads(json_match.group())

            chunks = []
            for i, chunk_data in enumerate(response_data.get('chunks', [])):
                chunk = {
                    'id': f"{original_doc['filename']}_{chunk_data.get('chunk_id', i)}",
                    'content': chunk_data['content'],
                    'metadata': {
                        **chunk_data['metadata'],
                        'source_file': original_doc['filename'],
                        'source_path': original_doc['file_path'],
                        'chunk_index': i
                    },
                    'word_count': len(chunk_data['content'].split()),
                    'char_count': len(chunk_data['content'])
                }
                chunks.append(chunk)

            return chunks

        except Exception as e:
            logger.error(f"Failed to parse AI chunking response: {e}")
            return self._fallback_chunking(original_doc)

    def _fallback_chunking(self, document: Dict) -> List[Dict]:
        """Simple fallback chunking when AI fails"""
        content = document['content']
        words = content.split()

        chunks = []
        chunk_size = 400  # Target words per chunk

        for i in range(0, len(words), chunk_size):
            chunk_words = words[i:i + chunk_size]
            chunk_content = ' '.join(chunk_words)

            chunk = {
                'id': f"{document['filename']}_fallback_{i // chunk_size}",
                'content': f"CONTEXT: {document['filename']} - Part {i // chunk_size + 1}\n\n{chunk_content}",
                'metadata': {
                    'source_file': document['filename'],
                    'source_path': document['file_path'],
                    'framework': 'Unknown',
                    'category': 'General',
                    'section': f"Part {i // chunk_size + 1}",
                    'keywords': [],
                    'language': 'unknown',
                    'chunk_type': 'fallback',
                    'chunk_index': i // chunk_size
                },
                'word_count': len(chunk_words),
                'char_count': len(chunk_content)
            }
            chunks.append(chunk)

        return chunks

    def _analyze_chunk_quality(self, chunks: List[Dict]) -> Dict:
        """Analyze the quality of generated chunks"""
        if not chunks:
            return {'error': 'No chunks to analyze'}

        word_counts = [chunk['word_count'] for chunk in chunks]
        languages = [chunk['metadata'].get('language', 'unknown') for chunk in chunks]
        frameworks = [chunk['metadata'].get('framework', 'Unknown') for chunk in chunks]

        return {
            'total_chunks': len(chunks),
            'word_count_stats': {
                'min': min(word_counts),
                'max': max(word_counts),
                'average': sum(word_counts) / len(word_counts),
                'target_range': self.chunk_size_range
            },
            'language_distribution': {lang: languages.count(lang) for lang in set(languages)},
            'framework_distribution': {fw: frameworks.count(fw) for fw in set(frameworks)},
            'quality_flags': self._identify_quality_issues(chunks)
        }

    def _identify_quality_issues(self, chunks: List[Dict]) -> List[str]:
        """Identify potential quality issues with chunks"""
        issues = []

        for chunk in chunks:
            word_count = chunk['word_count']
            chunk_id = chunk['id']

            # Check word count
            if word_count < self.chunk_size_range[0]:
                issues.append(f"Short chunk: {chunk_id} ({word_count} words)")
            elif word_count > self.chunk_size_range[1] * 1.5:
                issues.append(f"Long chunk: {chunk_id} ({word_count} words)")

            # Check for missing context headers
            if not chunk['content'].startswith(('CONTEXT:', 'FRAMEWORK:', '===')):
                issues.append(f"Missing context header: {chunk_id}")

            # Check metadata completeness
            metadata = chunk['metadata']
            if metadata.get('framework') == 'Unknown':
                issues.append(f"Unknown framework: {chunk_id}")

        return issues

    def _export_to_chromadb_format(self, chunks: List[Dict], output_dir: Path) -> Dict:
        """Export chunks in ChromaDB-ready format"""
        chromadb_data = {
            'chunks': chunks,
            'metadata': {
                'total_chunks': len(chunks),
                'export_date': datetime.now().isoformat(),
                'format': 'chromadb'
            }
        }

        output_path = output_dir / 'chunks_data.json'
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(chromadb_data, f, indent=2, ensure_ascii=False)

        return {
            'format': 'chromadb',
            'output_path': str(output_path),
            'chunks_exported': len(chunks)
        }

    def _export_to_custom_gpt_format(self, chunks: List[Dict], output_dir: Path) -> Dict:
        """Export chunks as individual markdown files for Custom GPT"""
        exported_files = []

        for i, chunk in enumerate(chunks):
            # Create filename
            framework = chunk['metadata'].get('framework', 'Unknown').replace(' ', '_')
            section = chunk['metadata'].get('section', 'Section').replace(' ', '_')
            filename = f"chunk_{i:03d}_{framework}_{section}.md"

            # Clean filename
            filename = "".join(c for c in filename if c.isalnum() or c in '._-')[:100] + '.md'

            # Write markdown file
            file_path = output_dir / filename
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(f"# {chunk['metadata'].get('framework', 'Management Framework')}\n\n")
                f.write(f"**Section:** {chunk['metadata'].get('section', 'General')}\n")
                f.write(f"**Category:** {chunk['metadata'].get('category', 'Management')}\n")
                f.write(f"**Keywords:** {', '.join(chunk['metadata'].get('keywords', []))}\n\n")
                f.write("---\n\n")
                f.write(chunk['content'])

            exported_files.append(str(file_path))

        return {
            'format': 'custom_gpt',
            'output_directory': str(output_dir),
            'files_exported': len(exported_files),
            'file_list': exported_files
        }
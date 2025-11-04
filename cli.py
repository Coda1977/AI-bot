#!/usr/bin/env python3
"""
Command Line Interface for Smart Materials Ingestion
"""

import click
import logging
from pathlib import Path
from rich.console import Console
from rich.table import Table
from rich.progress import Progress, SpinnerColumn, TextColumn
import json

from src.smart_ingestion import SmartMaterialsIngestion
from src.config import AppConfig

console = Console()

def setup_logging(level: str):
    """Setup logging configuration"""
    logging.basicConfig(
        level=getattr(logging, level.upper()),
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

@click.group()
@click.option('--log-level', default='INFO', help='Logging level')
@click.pass_context
def cli(ctx, log_level):
    """Smart Materials Ingestion System for Manager AI Assistant"""
    ctx.ensure_object(dict)
    setup_logging(log_level)
    ctx.obj['config'] = AppConfig.from_env()

@cli.command()
@click.option('--materials-dir', type=click.Path(exists=True, path_type=Path), help='Materials directory')
@click.option('--output-dir', type=click.Path(path_type=Path), help='Output directory')
@click.option('--ai-provider', type=click.Choice(['anthropic', 'openai', 'gemini']), help='AI provider')
@click.option('--formats', multiple=True, type=click.Choice(['chromadb', 'custom_gpt']), help='Output formats')
@click.pass_context
def ingest(ctx, materials_dir, output_dir, ai_provider, formats):
    """Run smart ingestion on materials directory"""
    config = ctx.obj['config']

    # Override config with CLI options
    if materials_dir:
        config.materials_dir = materials_dir
    if output_dir:
        config.output_dir = output_dir
    if ai_provider:
        config.ai.provider = ai_provider
    if formats:
        config.ingestion.output_formats = list(formats)

    # Validate inputs
    if not config.materials_dir.exists():
        console.print(f"❌ Materials directory not found: {config.materials_dir}", style="red")
        raise click.Abort()

    if not config.ai.api_key:
        console.print(f"❌ API key not found for {config.ai.provider}. Check your .env file.", style="red")
        raise click.Abort()

    console.print(f"🚀 Starting smart ingestion...", style="green")
    console.print(f"📁 Materials: {config.materials_dir}")
    console.print(f"📤 Output: {config.output_dir}")
    console.print(f"🤖 AI Provider: {config.ai.provider}")
    console.print(f"📋 Formats: {', '.join(config.ingestion.output_formats)}")

    try:
        # Initialize ingestion system
        ingestion = SmartMaterialsIngestion(
            ai_provider=config.ai.provider,
            api_key=config.ai.api_key,
            output_formats=config.ingestion.output_formats
        )

        # Run ingestion
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console
        ) as progress:
            task = progress.add_task("Processing materials...", total=None)

            report = ingestion.process_materials_directory(
                config.materials_dir,
                config.output_dir
            )

            progress.remove_task(task)

        # Display results
        display_ingestion_report(report)

    except Exception as e:
        console.print(f"❌ Ingestion failed: {e}", style="red")
        raise click.Abort()

@cli.command()
@click.argument('report_path', type=click.Path(exists=True, path_type=Path))
def report(report_path):
    """Display ingestion report"""
    try:
        with open(report_path, 'r', encoding='utf-8') as f:
            report_data = json.load(f)
        display_ingestion_report(report_data)
    except Exception as e:
        console.print(f"❌ Failed to load report: {e}", style="red")

@cli.command()
@click.option('--materials-dir', type=click.Path(path_type=Path), default=Path('materials'))
def check_materials(materials_dir):
    """Check what materials are available for processing"""
    if not materials_dir.exists():
        console.print(f"❌ Materials directory not found: {materials_dir}", style="red")
        return

    from src.document_processor import DocumentProcessor
    processor = DocumentProcessor()

    # Find all supported files
    supported_files = []
    for file_path in materials_dir.rglob('*'):
        if file_path.is_file() and file_path.suffix.lower() in processor.SUPPORTED_EXTENSIONS:
            stats = file_path.stat()
            supported_files.append({
                'name': file_path.name,
                'type': file_path.suffix.lower(),
                'size_kb': stats.st_size // 1024,
                'path': str(file_path.relative_to(materials_dir))
            })

    if not supported_files:
        console.print(f"❌ No supported files found in {materials_dir}", style="red")
        console.print(f"Supported formats: {', '.join(processor.SUPPORTED_EXTENSIONS)}")
        return

    # Display table
    table = Table(title=f"Materials Found in {materials_dir}")
    table.add_column("File Name")
    table.add_column("Type")
    table.add_column("Size (KB)")
    table.add_column("Path")

    for file_info in supported_files:
        table.add_row(
            file_info['name'],
            file_info['type'],
            str(file_info['size_kb']),
            file_info['path']
        )

    console.print(table)
    console.print(f"\n✅ Found {len(supported_files)} supported files")

def display_ingestion_report(report: dict):
    """Display a formatted ingestion report"""
    console.print("\n" + "="*60, style="blue")
    console.print("📊 SMART INGESTION REPORT", style="blue bold")
    console.print("="*60, style="blue")

    # Basic info
    console.print(f"📅 Date: {report['ingestion_date']}")
    console.print(f"🤖 AI Provider: {report['ai_provider']}")
    console.print(f"📁 Source: {report['source_directory']}")
    console.print(f"📤 Output: {report['output_directory']}")

    # Processing summary
    processing = report['processing_summary']
    console.print(f"\n📋 Document Processing:")
    console.print(f"  • Total files: {processing['total_files']}")
    console.print(f"  • Successful: {processing['successful']}")
    console.print(f"  • Failed: {processing['failed']}")
    console.print(f"  • Total words: {processing['total_words']:,}")

    # File types
    if processing['file_types']:
        console.print(f"  • File types: {dict(processing['file_types'])}")

    # Chunking results
    chunking = report['chunking_results']
    console.print(f"\n🔪 Chunking Results:")
    console.print(f"  • Total chunks: {chunking['total_chunks_created']}")
    console.print(f"  • Average chunk size: {chunking['average_chunk_size_words']:.1f} words")
    console.print(f"  • Documents processed: {chunking['successful_documents']}")

    # Quality metrics
    if 'quality_metrics' in report and 'quality_flags' in report['quality_metrics']:
        quality = report['quality_metrics']
        console.print(f"\n⚡ Quality Analysis:")

        word_stats = quality['word_count_stats']
        console.print(f"  • Word count range: {word_stats['min']}-{word_stats['max']} (avg: {word_stats['average']:.1f})")
        console.print(f"  • Target range: {word_stats['target_range']}")

        if quality['quality_flags']:
            console.print(f"  ⚠️  Issues found: {len(quality['quality_flags'])}")
            for issue in quality['quality_flags'][:5]:  # Show first 5 issues
                console.print(f"    - {issue}")
        else:
            console.print(f"  ✅ No quality issues detected")

    # Export results
    console.print(f"\n📦 Export Results:")
    for format_name, format_data in report['export_results'].items():
        if format_name == 'chromadb':
            console.print(f"  • ChromaDB: {format_data['chunks_exported']} chunks → {format_data['output_path']}")
        elif format_name == 'custom_gpt':
            console.print(f"  • Custom GPT: {format_data['files_exported']} files → {format_data['output_directory']}")

    # Failed documents
    if report['failed_documents']:
        console.print(f"\n❌ Failed Documents:")
        for failed_doc in report['failed_documents']:
            console.print(f"  • {failed_doc['filename']}: {failed_doc.get('error_message', 'Unknown error')}")

    console.print("\n" + "="*60, style="blue")

if __name__ == '__main__':
    cli()
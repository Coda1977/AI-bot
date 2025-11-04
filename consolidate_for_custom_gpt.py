#!/usr/bin/env python3
"""
Consolidate 816 chunks into ~20 larger files for Custom GPT upload
"""

import os
import json
from pathlib import Path
from collections import defaultdict

def consolidate_chunks_for_custom_gpt():
    """Consolidate chunks into larger files suitable for Custom GPT"""

    print("🔄 Consolidating 816 chunks into Custom GPT-compatible files...")

    # Paths
    chunks_dir = Path("output/custom_gpt_files")
    consolidated_dir = Path("output/custom_gpt_consolidated")
    consolidated_dir.mkdir(exist_ok=True)

    if not chunks_dir.exists():
        print("❌ No chunks directory found")
        return

    # Load ingestion report to understand the source files
    report_path = Path("output/ingestion_report.json")
    if report_path.exists():
        with open(report_path, 'r') as f:
            report = json.load(f)
        print(f"📊 Processing {report['chunking_results']['total_chunks_created']} chunks")

    # Group chunks by source document
    source_groups = defaultdict(list)

    # Read all chunk files and group by source
    chunk_files = list(chunks_dir.glob("*.md"))
    print(f"📁 Found {len(chunk_files)} chunk files")

    for chunk_file in chunk_files:
        try:
            with open(chunk_file, 'r', encoding='utf-8') as f:
                content = f.read()

            # Extract source from context line
            lines = content.split('\n')
            context_line = None
            for line in lines:
                if line.startswith('CONTEXT:'):
                    context_line = line
                    break

            if context_line:
                # Extract source file name from context
                source = context_line.replace('CONTEXT:', '').split(' - Part')[0].strip()
                source_groups[source].append({
                    'file': chunk_file,
                    'content': content,
                    'size': len(content.split())
                })
            else:
                # Fallback grouping
                source_groups['Unknown'].append({
                    'file': chunk_file,
                    'content': content,
                    'size': len(content.split())
                })

        except Exception as e:
            print(f"⚠️ Error reading {chunk_file}: {e}")

    print(f"📚 Grouped into {len(source_groups)} source documents")

    # Create consolidated files by framework/topic
    consolidated_files = {}

    # Framework-based groupings
    framework_groups = {
        'Feedback_and_Communication': ['Giving Feedback', 'Recieving Feedback', 'FeedForward'],
        'Leadership_and_Management': ['Manager Core', 'High Output Management', 'First 90 Days'],
        'Performance_and_Accountability': ['5 accountabilities', 'ManagingYourself'],
        'Coaching_and_Development': ['Coaching', 'Strengths', 'reflected best self'],
        'Productivity_and_Time': ['80-20 productivity', 'Time Talent Energy', 'tiny habits'],
        'Strategic_Thinking': ['Pyramid principle', 'the new how', 'messaging'],
        'Team_Building': ['team meetings', 'relationship building', 'ביטחון פסיכולוגי'],
        'Motivation_and_Engagement': ['Motivation Features', 'motivation features', 'primed to perform', 'job crafting'],
        'Delegation_and_Authority': ['delegation', 'agency'],
        'Interview_and_Retention': ['stay interview'],
        'Habits_and_Behavior': ['Marshall-Goldsmith', 'distinctions'],
        'Work_Design': ['great work map', 'Red thread map', 'expectation alignment']
    }

    # Assign sources to framework groups
    source_to_framework = {}
    for framework, keywords in framework_groups.items():
        for source in source_groups.keys():
            for keyword in keywords:
                if keyword.lower() in source.lower():
                    source_to_framework[source] = framework
                    break

    # Group chunks by framework
    framework_chunks = defaultdict(list)
    for source, chunks in source_groups.items():
        framework = source_to_framework.get(source, 'General_Management')
        framework_chunks[framework].extend(chunks)

    # Create consolidated files
    file_count = 0
    total_words = 0

    for framework, chunks in framework_chunks.items():
        if not chunks:
            continue

        file_count += 1
        framework_words = sum(chunk['size'] for chunk in chunks)
        total_words += framework_words

        # Sort chunks by source and part number for logical order
        chunks.sort(key=lambda x: (x['file'].name))

        # Create consolidated content
        consolidated_content = f"# {framework.replace('_', ' ')} Framework Collection\n\n"
        consolidated_content += f"**Framework Category:** {framework.replace('_', ' ')}\n"
        consolidated_content += f"**Number of Sources:** {len(set(chunk['content'].split('CONTEXT:')[1].split(' - Part')[0].strip() if 'CONTEXT:' in chunk['content'] else 'Unknown' for chunk in chunks))}\n"
        consolidated_content += f"**Total Content:** {framework_words:,} words\n\n"
        consolidated_content += "---\n\n"

        # Add all chunks for this framework
        current_source = None
        for i, chunk in enumerate(chunks):
            # Extract source from content
            chunk_content = chunk['content']
            if 'CONTEXT:' in chunk_content:
                context_line = [line for line in chunk_content.split('\n') if line.startswith('CONTEXT:')][0]
                source = context_line.replace('CONTEXT:', '').split(' - Part')[0].strip()

                if source != current_source:
                    current_source = source
                    consolidated_content += f"\n## Source: {source}\n\n"

            # Add chunk content (remove the individual headers)
            content_parts = chunk_content.split('---\n\n', 1)
            if len(content_parts) > 1:
                main_content = content_parts[1]
                consolidated_content += main_content + "\n\n---\n\n"
            else:
                consolidated_content += chunk_content + "\n\n---\n\n"

        # Write consolidated file
        safe_filename = framework.replace(' ', '_').replace('/', '_')
        output_file = consolidated_dir / f"{safe_filename}.md"

        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(consolidated_content)

        print(f"✅ {framework}: {len(chunks)} chunks → {framework_words:,} words → {output_file.name}")

    # Create summary file
    summary_content = f"""# Management Framework Collection - Summary

**Total Original Files:** 37 management documents
**Total Chunks Created:** 816 individual chunks
**Total Content:** {total_words:,} words
**Consolidated Into:** {file_count} framework collections

## Framework Categories Included:

"""

    for framework, chunks in framework_chunks.items():
        if chunks:
            framework_words = sum(chunk['size'] for chunk in chunks)
            sources = set()
            for chunk in chunks:
                if 'CONTEXT:' in chunk['content']:
                    context_line = [line for line in chunk['content'].split('\n') if line.startswith('CONTEXT:')][0]
                    source = context_line.replace('CONTEXT:', '').split(' - Part')[0].strip()
                    sources.add(source)

            summary_content += f"### {framework.replace('_', ' ')}\n"
            summary_content += f"- **Content:** {framework_words:,} words\n"
            summary_content += f"- **Sources:** {len(sources)} documents\n"
            summary_content += f"- **Key Materials:** {', '.join(list(sources)[:3])}{'...' if len(sources) > 3 else ''}\n\n"

    summary_content += f"""
## Usage Instructions

These files are optimized for ChatGPT Custom GPT upload:

1. **Upload all {file_count} .md files** to your Custom GPT
2. **Use the system prompt** from `system_prompts/custom_gpt_prompt.txt`
3. **Test with management questions** to validate the knowledge

## Content Coverage

Your Custom GPT will have comprehensive knowledge about:
- Performance management and feedback
- Leadership and team development
- Strategic thinking and communication
- Productivity and time management
- Coaching and employee development
- Delegation and authority
- Motivation and engagement
- And much more!

**Ready for immediate Custom GPT deployment!** 🚀
"""

    summary_file = consolidated_dir / "00_SUMMARY.md"
    with open(summary_file, 'w', encoding='utf-8') as f:
        f.write(summary_content)

    print(f"\n📋 CONSOLIDATION COMPLETE!")
    print(f"✅ {file_count + 1} files created (including summary)")
    print(f"📊 Total content: {total_words:,} words")
    print(f"📁 Location: {consolidated_dir}")
    print(f"🎯 Ready for Custom GPT upload!")

    return file_count + 1

if __name__ == "__main__":
    consolidate_chunks_for_custom_gpt()
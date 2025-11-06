#!/usr/bin/env python3
"""
Immediate search improvements without heavy dependencies
Phase 1A: Improve existing search to be more effective
"""
import json
import os
from pathlib import Path

def update_api_with_improved_search():
    """Update the API with better search algorithm"""

    api_file = Path("api/index.py")
    if not api_file.exists():
        print("❌ API file not found")
        return False

    # Read current API
    with open(api_file, 'r', encoding='utf-8') as f:
        content = f.read()

    # Create improved search function
    improved_search_function = '''async def search_by_keywords_improved(query: str, top_k: int = 5) -> List[SearchResult]:
    """Enhanced keyword-based search with fuzzy matching and semantic understanding"""
    try:
        # Load local knowledge base for better search
        knowledge_file = Path("output/chromadb_data/chunks_data.json")
        if not knowledge_file.exists():
            # Try alternative paths
            alt_paths = [
                Path("../output/chromadb_data/chunks_data.json"),
                Path("chunks_data.json"),
            ]
            for alt_path in alt_paths:
                if alt_path.exists():
                    knowledge_file = alt_path
                    break
            else:
                logger.warning("Knowledge base file not found for improved search")
                return await search_by_pinecone_metadata(query, top_k)

        with open(knowledge_file, 'r', encoding='utf-8') as f:
            data = json.load(f)

        chunks = data.get('chunks', [])
        query_words = query.lower().split()

        # Enhanced scoring system
        scored_chunks = []
        for chunk in chunks:
            content = chunk['content'].lower()
            source_file = chunk['metadata'].get('source_file', '').lower()
            framework = chunk['metadata'].get('framework', '').lower()

            score = 0

            # 1. Exact phrase matching (highest weight)
            if query.lower() in content:
                score += 100

            # 2. Source file matching
            for word in query_words:
                if len(word) > 2:
                    if word in source_file:
                        score += 50
                    if word in framework:
                        score += 30

            # 3. Individual word matching
            for word in query_words:
                if len(word) > 2:
                    count = content.count(word)
                    score += count * len(word) * 5

            # 4. Semantic keyword boosting
            semantic_matches = {
                'feedback': ['giving', 'receiving', 'sbi', 'situation', 'behavior', 'impact', 'radical', 'candor'],
                'coaching': ['development', '1:1', 'growth', 'mentoring', 'guidance'],
                'delegation': ['authority', 'responsibility', 'accountability', 'decision'],
                'leadership': ['management', 'leading', 'influence', 'direction'],
                'communication': ['conversation', 'discussion', 'talking', 'speaking']
            }

            for category, keywords in semantic_matches.items():
                if category in query.lower():
                    for keyword in keywords:
                        if keyword in content:
                            score += 20

            # 5. Framework-specific boosting
            if 'feedback' in query.lower() and any(term in content for term in ['situation', 'behavior', 'impact']):
                score += 50
            if 'coaching' in query.lower() and any(term in content for term in ['development', 'growth', 'conversation']):
                score += 50

            if score > 0:
                scored_chunks.append((chunk, score))

        # Sort by score and return results
        scored_chunks.sort(key=lambda x: x[1], reverse=True)

        results = []
        for chunk, score in scored_chunks[:top_k]:
            results.append(SearchResult(
                id=chunk['id'],
                content=chunk['content'],
                metadata={
                    'source_file': chunk['metadata'].get('source_file', 'Unknown'),
                    'framework': chunk['metadata'].get('framework', 'Unknown'),
                    'category': chunk['metadata'].get('category', 'General'),
                    'section': chunk['metadata'].get('section', ''),
                    'word_count': chunk.get('word_count', 0)
                },
                score=float(score) / 100.0
            ))

        logger.info(f"Enhanced search found {len(results)} results for '{query}'")
        return results

    except Exception as e:
        logger.error(f"Enhanced search failed: {e}")
        # Fallback to Pinecone metadata search
        return await search_by_pinecone_metadata(query, top_k)

async def search_by_pinecone_metadata(query: str, top_k: int = 5) -> List[SearchResult]:
    """Fallback search using Pinecone metadata when local files aren't available"""
    try:
        index = get_pinecone_index()
        namespace = "management-knowledge"

        query_words = query.lower().split()
        dummy_embedding = [0.1] * 1536

        search_results = index.query(
            vector=dummy_embedding,
            top_k=min(100, top_k * 10),  # Get more results to filter
            include_metadata=True,
            namespace=namespace
        )

        scored_results = []
        for match in search_results.matches:
            metadata = match.metadata or {}
            content = metadata.get('content', '').lower()
            source_file = metadata.get('source_file', '').lower()
            framework = metadata.get('framework', '').lower()

            score = 0

            # Enhanced Pinecone metadata scoring
            for word in query_words:
                if len(word) > 2:
                    # Source file matches
                    if word in source_file:
                        score += 50
                    # Framework matches
                    if word in framework:
                        score += 30
                    # Content matches
                    if word in content:
                        score += content.count(word) * 10

            # Specific content type boosting
            if 'feedback' in query.lower():
                if 'feedback' in source_file or 'feedback' in framework:
                    score += 100
                if any(term in content for term in ['situation', 'behavior', 'impact', 'sbi', 'radical', 'candor']):
                    score += 50

            if score > 0 or 'feedback' in source_file:  # Always include feedback files
                scored_results.append((match, score))

        scored_results.sort(key=lambda x: x[1], reverse=True)

        results = []
        for match, score in scored_results[:top_k]:
            content = match.metadata.get('content', '')
            if not content:
                content = await get_full_content_by_id(match.id)

            results.append(SearchResult(
                id=match.id,
                content=content,
                metadata={
                    'source_file': match.metadata.get('source_file', 'Unknown'),
                    'framework': match.metadata.get('framework', 'Unknown'),
                    'category': match.metadata.get('category', 'General'),
                    'section': match.metadata.get('section', ''),
                    'word_count': match.metadata.get('word_count', 0)
                },
                score=float(score) / 100.0 if score > 0 else float(match.score)
            ))

        return results

    except Exception as e:
        logger.error(f"Pinecone metadata search failed: {e}")
        return []'''

    # Replace the search function
    if 'async def search_by_keywords(' in content:
        # Find the function and replace it
        start_marker = 'async def search_by_keywords('
        end_marker = 'async def search_knowledge('

        start_idx = content.find(start_marker)
        end_idx = content.find(end_marker)

        if start_idx != -1 and end_idx != -1:
            new_content = (
                content[:start_idx] +
                improved_search_function + '\n\n' +
                content[end_idx:]
            )

            # Update the call to use the improved function
            new_content = new_content.replace(
                'keyword_results = await search_by_keywords(request.query, request.top_k)',
                'keyword_results = await search_by_keywords_improved(request.query, request.top_k)'
            )

            # Write the updated file
            with open(api_file, 'w', encoding='utf-8') as f:
                f.write(new_content)

            print("✅ API updated with improved search algorithm")
            return True

    print("❌ Could not update API file")
    return False

def create_test_questions():
    """Create comprehensive test questions for validation"""
    test_questions = [
        # Feedback questions
        {
            "question": "how to give difficult feedback",
            "expected_frameworks": ["SBI", "Situation Behavior Impact", "Radical Candor"],
            "expected_sources": ["Giving Feedback.pptx", "core training materials"]
        },
        {
            "question": "SBI feedback framework situation behavior impact",
            "expected_frameworks": ["SBI Framework", "Feedback"],
            "expected_sources": ["Giving Feedback.pptx"]
        },
        {
            "question": "radical candor feedback approach",
            "expected_frameworks": ["Radical Candor"],
            "expected_sources": ["Giving Feedback.pptx"]
        },

        # Coaching questions
        {
            "question": "coaching conversations for employee development",
            "expected_frameworks": ["Coaching Framework"],
            "expected_sources": ["core training materials", "coaching"]
        },
        {
            "question": "1:1 meeting structure and framework",
            "expected_frameworks": ["1:1 Framework"],
            "expected_sources": ["core training materials"]
        },

        # Delegation questions
        {
            "question": "delegation authority levels decision making",
            "expected_frameworks": ["Delegation Framework"],
            "expected_sources": ["core training materials"]
        },
        {
            "question": "how to delegate responsibility effectively",
            "expected_frameworks": ["Delegation"],
            "expected_sources": ["core training materials"]
        },

        # Leadership questions
        {
            "question": "leadership development management skills",
            "expected_frameworks": ["Leadership", "Management"],
            "expected_sources": ["First 90 Days", "core training materials"]
        }
    ]

    # Save test questions
    test_file = Path("test_questions.json")
    with open(test_file, 'w', encoding='utf-8') as f:
        json.dump(test_questions, f, indent=2)

    print(f"✅ Created {len(test_questions)} test questions in {test_file}")
    return test_questions

def run_search_tests():
    """Test the improved search with key questions"""
    test_questions = [
        "giving feedback SBI situation behavior impact",
        "radical candor feedback framework",
        "coaching employee development conversation",
        "delegation authority responsibility",
        "difficult feedback conversations"
    ]

    print("🧪 Testing improved search system...")

    try:
        import requests
        api_url = "https://ai-bot-nine-chi.vercel.app/api/search"

        results = {}
        for query in test_questions:
            print(f"\\n🔍 Testing: '{query}'")

            try:
                response = requests.post(api_url, json={"query": query, "top_k": 5}, timeout=10)
                if response.status_code == 200:
                    data = response.json()
                    search_results = data.get('results', [])
                    print(f"  ✅ Found {len(search_results)} results")

                    for i, result in enumerate(search_results[:3]):
                        source = result['metadata']['source_file']
                        score = result['score']
                        content_preview = result['content'][:100] + "..." if len(result['content']) > 100 else result['content']
                        print(f"    {i+1}. {source} (score: {score:.2f})")
                        print(f"       {content_preview}")

                    results[query] = {
                        'count': len(search_results),
                        'top_source': search_results[0]['metadata']['source_file'] if search_results else 'None',
                        'success': len(search_results) > 0
                    }
                else:
                    print(f"  ❌ API error: {response.status_code}")
                    results[query] = {'success': False, 'error': response.status_code}

            except Exception as e:
                print(f"  ❌ Request failed: {e}")
                results[query] = {'success': False, 'error': str(e)}

        # Summary
        successful = sum(1 for r in results.values() if r.get('success', False))
        print(f"\\n📊 Test Summary: {successful}/{len(test_questions)} queries successful")

        # Check for key content
        feedback_found = any('feedback' in r.get('top_source', '').lower() for r in results.values() if r.get('success'))
        print(f"🎯 Feedback content found: {'✅' if feedback_found else '❌'}")

        return results

    except Exception as e:
        print(f"❌ Testing failed: {e}")
        return {}

if __name__ == "__main__":
    print("=" * 60)
    print("🚀 IMMEDIATE SEARCH IMPROVEMENTS")
    print("Phase 1A: Enhance existing search algorithm")
    print("=" * 60)

    # Update the API
    if update_api_with_improved_search():
        print("\\n✅ API updated with enhanced search")

        # Create test questions
        create_test_questions()

        print("\\n⏳ Waiting 30 seconds for deployment...")
        import time
        time.sleep(30)

        # Test the improvements
        print("\\n" + "=" * 40)
        print("🧪 TESTING IMPROVED SEARCH")
        print("=" * 40)
        run_search_tests()

    else:
        print("\\n❌ Failed to update API")

    print("\\n" + "=" * 60)
    print("🎯 NEXT STEPS:")
    print("1. Commit and deploy the improved search")
    print("2. Test with Custom GPT")
    print("3. Proceed with Phase 2: Hybrid Architecture")
    print("=" * 60)
#!/usr/bin/env python3
"""
Test script for RAG API
"""

import requests
import json
import time

API_BASE = "http://localhost:8000"

def test_health_check():
    """Test the health check endpoint"""
    print("Testing health check...")
    response = requests.get(f"{API_BASE}/health")
    print(f"Status: {response.status_code}")
    print(f"Response: {json.dumps(response.json(), indent=2)}")
    return response.status_code == 200

def test_search():
    """Test the search endpoint"""
    print("\nTesting search endpoint...")
    search_data = {
        "query": "How to give feedback to underperforming employees",
        "max_results": 3
    }

    response = requests.post(f"{API_BASE}/search", json=search_data)
    print(f"Status: {response.status_code}")

    if response.status_code == 200:
        results = response.json()
        print(f"Found {results['total_results']} results")
        for i, result in enumerate(results['results']):
            print(f"\nResult {i+1}:")
            print(f"Source: {result['source_file']}")
            print(f"Relevance: {result['relevance_score']:.3f}")
            print(f"Content: {result['content'][:200]}...")
    else:
        print(f"Error: {response.text}")

    return response.status_code == 200

def test_ask():
    """Test the ask endpoint"""
    print("\nTesting ask endpoint...")
    ask_data = {
        "query": "How should I handle a team member who constantly interrupts others in meetings?",
        "detail_level": "detailed"
    }

    response = requests.post(f"{API_BASE}/ask", json=ask_data)
    print(f"Status: {response.status_code}")

    if response.status_code == 200:
        result = response.json()
        print(f"AI Provider: {result['ai_provider']}")
        print(f"Sources used: {len(result['sources'])}")
        print(f"\nAnswer:\n{result['answer']}")

        print(f"\nSources:")
        for i, source in enumerate(result['sources']):
            print(f"{i+1}. {source['source_file']} (relevance: {source['relevance_score']:.3f})")
    else:
        print(f"Error: {response.text}")

    return response.status_code == 200

def main():
    """Run all tests"""
    print("RAG API Test Suite")
    print("=" * 50)

    # Wait a moment for the server to start
    print("Waiting for server to be ready...")
    time.sleep(2)

    tests = [
        ("Health Check", test_health_check),
        ("Search", test_search),
        ("Ask Question", test_ask)
    ]

    results = {}
    for test_name, test_func in tests:
        try:
            results[test_name] = test_func()
        except Exception as e:
            print(f"Test {test_name} failed with error: {e}")
            results[test_name] = False

    print("\n" + "=" * 50)
    print("Test Results:")
    for test_name, passed in results.items():
        status = "PASS" if passed else "FAIL"
        print(f"{test_name}: {status}")

    all_passed = all(results.values())
    print(f"\nOverall: {'PASS' if all_passed else 'FAIL'}")
    return all_passed

if __name__ == "__main__":
    main()
#!/usr/bin/env python3
"""
Simple test to verify the project structure and basic imports
"""

import os
import sys
from pathlib import Path

def test_project_structure():
    """Test that the project structure is correct"""
    print("🏗️  Testing project structure...")

    required_files = [
        "src/__init__.py",
        "src/document_processor.py",
        "src/ai_client.py",
        "src/smart_ingestion.py",
        "src/config.py",
        "requirements.txt",
        "cli.py",
        ".env.example",
        "README.md"
    ]

    required_dirs = [
        "src",
        "materials",
        "output",
        "system_prompts",
        "tests"
    ]

    missing_files = []
    missing_dirs = []

    # Check files
    for file_path in required_files:
        if not Path(file_path).exists():
            missing_files.append(file_path)
        else:
            print(f"  ✅ {file_path}")

    # Check directories
    for dir_path in required_dirs:
        if not Path(dir_path).exists():
            missing_dirs.append(dir_path)
        else:
            print(f"  ✅ {dir_path}/")

    if missing_files:
        print(f"  ❌ Missing files: {missing_files}")

    if missing_dirs:
        print(f"  ❌ Missing directories: {missing_dirs}")

    return len(missing_files) == 0 and len(missing_dirs) == 0

def test_materials():
    """Test that sample materials exist"""
    print("\n📚 Testing materials...")

    materials_dir = Path("materials")
    if not materials_dir.exists():
        print("  ❌ Materials directory not found")
        return False

    materials = list(materials_dir.glob("*"))
    if not materials:
        print("  ⚠️  No materials found - add your documents to materials/")
        return False

    print(f"  ✅ Found {len(materials)} files:")
    for material in materials:
        if material.is_file():
            print(f"    • {material.name}")

    return True

def test_system_prompts():
    """Test that system prompts exist"""
    print("\n💬 Testing system prompts...")

    prompts_dir = Path("system_prompts")
    prompts = list(prompts_dir.glob("*.txt"))

    if not prompts:
        print("  ❌ No system prompts found")
        return False

    print(f"  ✅ Found {len(prompts)} prompt files:")
    for prompt in prompts:
        print(f"    • {prompt.name}")

    return True

def test_env_example():
    """Test that .env.example is properly configured"""
    print("\n⚙️  Testing configuration...")

    env_file = Path(".env.example")
    if not env_file.exists():
        print("  ❌ .env.example not found")
        return False

    content = env_file.read_text()
    required_vars = [
        "AI_PROVIDER",
        "ANTHROPIC_API_KEY",
        "OPENAI_API_KEY",
        "GOOGLE_API_KEY"
    ]

    missing_vars = []
    for var in required_vars:
        if var not in content:
            missing_vars.append(var)
        else:
            print(f"  ✅ {var} configured")

    if missing_vars:
        print(f"  ❌ Missing variables: {missing_vars}")
        return False

    return True

def check_readme():
    """Check that README has key sections"""
    print("\n📖 Testing documentation...")

    readme = Path("README.md")
    if not readme.exists():
        print("  ❌ README.md not found")
        return False

    content = readme.read_text().lower()
    required_sections = [
        "quick start",
        "installation",
        "configuration",
        "supported formats",
        "custom gpt"
    ]

    missing_sections = []
    for section in required_sections:
        if section not in content:
            missing_sections.append(section)
        else:
            print(f"  ✅ {section} section found")

    if missing_sections:
        print(f"  ⚠️  Missing sections: {missing_sections}")

    return len(missing_sections) == 0

if __name__ == "__main__":
    print("🚀 Smart Ingestion System - Structure Test\n")

    tests = [
        ("Project Structure", test_project_structure),
        ("Materials", test_materials),
        ("System Prompts", test_system_prompts),
        ("Configuration", test_env_example),
        ("Documentation", check_readme)
    ]

    passed = 0
    total = len(tests)

    for test_name, test_func in tests:
        try:
            if test_func():
                passed += 1
        except Exception as e:
            print(f"  ❌ {test_name} test failed: {e}")

    print(f"\n📊 Results: {passed}/{total} tests passed")

    if passed == total:
        print("✅ All structure tests passed!")
        print("\n🎯 Next steps:")
        print("  1. Install dependencies: python3 -m pip install -r requirements.txt --user")
        print("  2. Copy .env.example to .env and add your API key")
        print("  3. Add your management materials to materials/")
        print("  4. Run: python3 cli.py ingest")
    else:
        print("❌ Some tests failed - check the structure above")

    print("\n" + "="*50)
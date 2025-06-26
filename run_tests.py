#!/usr/bin/env python3
"""
Test runner for Recipe Chat Assistant

Usage:
    python run_tests.py              # Run all tests
    python run_tests.py auth         # Run auth tests only
    python run_tests.py -v           # Run with verbose output
    python run_tests.py --coverage   # Run with coverage report
"""

import sys
import subprocess
import os


def main():
    # Base pytest command
    cmd = ["python", "-m", "pytest"]
    
    # Add default options
    cmd.extend(["-v", "--tb=short"])
    
    # Check for coverage flag
    if "--coverage" in sys.argv:
        cmd.extend(["--cov=src", "--cov-report=html", "--cov-report=term"])
        sys.argv.remove("--coverage")
    
    # Add any remaining arguments
    if len(sys.argv) > 1:
        # If specific test module requested
        if sys.argv[1] in ["auth", "database", "recipes", "llm", "websocket"]:
            cmd.append(f"tests/test_{sys.argv[1]}.py")
        else:
            cmd.extend(sys.argv[1:])
    
    # Set environment for testing
    os.environ["DATABASE_URL"] = "sqlite+aiosqlite:///:memory:"
    os.environ["JWT_SECRET_KEY"] = "test-secret-key"
    os.environ["GOOGLE_API_KEY"] = "test-api-key"
    os.environ["GOOGLE_OPENAI_BASE_URL"] = "https://test.url"
    os.environ["TESTING"] = "true"
    
    # Run tests
    print(f"Running: {' '.join(cmd)}")
    result = subprocess.run(cmd)
    
    return result.returncode


if __name__ == "__main__":
    sys.exit(main())
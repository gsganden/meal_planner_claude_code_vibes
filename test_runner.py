#!/usr/bin/env python3
"""
Simple test runner to verify database isolation fixes
"""
import subprocess
import sys

def run_tests():
    """Run tests and check for database isolation issues"""
    print("Running auth tests...")
    result = subprocess.run(
        ["python", "-m", "pytest", "tests/test_auth.py", "-v", "--tb=short"],
        capture_output=True,
        text=True
    )
    
    print("STDOUT:")
    print(result.stdout)
    print("\nSTDERR:")
    print(result.stderr)
    print(f"\nReturn code: {result.returncode}")
    
    # Check for common database isolation issues
    if "email already exists" in result.stdout or "email already exists" in result.stderr:
        print("\n❌ Database isolation issue detected: email already exists")
        return False
    
    if result.returncode != 0:
        print("\n❌ Tests failed")
        return False
    
    print("\n✅ Auth tests passed!")
    
    # Run database tests
    print("\n\nRunning database tests...")
    result = subprocess.run(
        ["python", "-m", "pytest", "tests/test_database.py", "-v", "--tb=short"],
        capture_output=True,
        text=True
    )
    
    print("STDOUT:")
    print(result.stdout)
    print("\nSTDERR:")
    print(result.stderr)
    
    if result.returncode != 0:
        print("\n❌ Database tests failed")
        return False
    
    print("\n✅ Database tests passed!")
    
    # Run all tests together to check for conflicts
    print("\n\nRunning all tests together...")
    result = subprocess.run(
        ["python", "-m", "pytest", "tests/test_auth.py", "tests/test_database.py", "tests/test_recipes.py", "-v", "--tb=short"],
        capture_output=True,
        text=True
    )
    
    if "email already exists" in result.stdout or "email already exists" in result.stderr:
        print("\n❌ Database isolation issue when running tests together")
        return False
    
    if result.returncode != 0:
        print("\n❌ Tests failed when run together")
        return False
    
    print("\n✅ All tests passed when run together!")
    return True

if __name__ == "__main__":
    success = run_tests()
    sys.exit(0 if success else 1)
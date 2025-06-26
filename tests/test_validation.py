import pytest
from src.utils.validation import (
    sanitize_string,
    sanitize_recipe_data,
    is_valid_email,
    is_valid_url,
    validate_password_strength,
    sanitize_filename,
    validate_recipe_completeness
)


def test_sanitize_string():
    """Test string sanitization"""
    # HTML tags should be stripped (bleach strips tags)
    assert sanitize_string("<script>alert('xss')</script>") == "alert('xss')"
    
    # Whitespace should be trimmed
    assert sanitize_string("  hello world  ") == "hello world"
    
    # Length limiting
    assert sanitize_string("a" * 100, max_length=10) == "a" * 10
    
    # Non-string input
    assert sanitize_string(None) == ""
    assert sanitize_string(123) == ""


def test_sanitize_recipe_data():
    """Test recipe data sanitization"""
    recipe = {
        "title": "<b>Test Recipe</b>",
        "description": "<script>alert('xss')</script>Description",
        "yield": "  4 servings  ",
        "ingredients": [
            {"text": "<i>2 cups</i> flour", "quantity": "2", "unit": " cup "},
            {"text": "a" * 300, "quantity": "1", "unit": ""}
        ],
        "steps": [
            {"order": 1, "text": "<p>Step 1</p>"},
            {"order": 2, "text": "Step 2" + "!" * 2000}
        ],
        "tags": ["<tag1>", "tag2", "tag3"] + ["extra"] * 30,
        "source": {
            "type": "url",
            "url": "javascript:alert('xss')",
            "file_name": "../../../etc/passwd"
        }
    }
    
    sanitized = sanitize_recipe_data(recipe)
    
    # Check sanitization
    assert sanitized["title"] == "Test Recipe"  # Tags stripped
    assert sanitized["description"] == "alert('xss')Description"  # Script tag stripped
    assert sanitized["yield"] == "4 servings"
    assert sanitized["ingredients"][0]["text"] == "2 cups flour"  # Tags stripped
    assert sanitized["ingredients"][0]["unit"] == "cup"
    assert len(sanitized["ingredients"][1]["text"]) == 200  # Limited
    assert sanitized["steps"][0]["text"] == "Step 1"  # Tags stripped
    assert len(sanitized["steps"][1]["text"]) == 1000  # Limited
    assert len(sanitized["tags"]) == 20  # Limited to 20
    assert sanitized["source"]["url"] == ""  # Invalid URL cleared
    assert "../" not in sanitized["source"]["file_name"]


def test_email_validation():
    """Test email validation"""
    # Valid emails
    assert is_valid_email("user@example.com")
    assert is_valid_email("first.last@example.co.uk")
    assert is_valid_email("user+tag@example.com")
    
    # Invalid emails
    assert not is_valid_email("invalid")
    assert not is_valid_email("@example.com")
    assert not is_valid_email("user@")
    assert not is_valid_email("user @example.com")
    assert not is_valid_email("user@example")


def test_url_validation():
    """Test URL validation"""
    # Valid URLs
    assert is_valid_url("https://example.com")
    assert is_valid_url("http://example.com/path/to/page")
    assert is_valid_url("https://sub.example.com:8080/page?param=value")
    
    # Invalid URLs
    assert not is_valid_url("javascript:alert('xss')")
    assert not is_valid_url("ftp://example.com")
    assert not is_valid_url("example.com")
    assert not is_valid_url("http://")


def test_password_validation():
    """Test password strength validation"""
    # Valid password
    assert validate_password_strength("ValidPass123") == []
    
    # Too short
    issues = validate_password_strength("Pass1")
    assert any("8 characters" in issue for issue in issues)
    
    # No letter
    issues = validate_password_strength("12345678")
    assert any("letter" in issue for issue in issues)
    
    # No number
    issues = validate_password_strength("ValidPassword")
    assert any("number" in issue for issue in issues)
    
    # Multiple issues
    issues = validate_password_strength("short")
    assert len(issues) >= 2


def test_sanitize_filename():
    """Test filename sanitization"""
    # Remove path components
    assert sanitize_filename("/etc/passwd") == "passwd"
    assert sanitize_filename("..\\..\\windows\\system32\\config") == "config"
    
    # Remove dangerous characters
    assert sanitize_filename("file<>:|?*.txt") == "file.txt"
    
    # Replace spaces
    assert sanitize_filename("my file name.pdf") == "my_file_name.pdf"
    
    # Handle multiple dots
    assert sanitize_filename("file...name...txt") == "file_name_.txt"
    
    # Length limiting
    long_name = "a" * 300 + ".txt"
    sanitized = sanitize_filename(long_name)
    assert len(sanitized) <= 255
    assert sanitized.endswith(".txt")


def test_recipe_completeness_validation():
    """Test recipe completeness validation"""
    # Complete recipe with all optional fields
    complete_recipe = {
        "title": "Test Recipe",
        "yield": "4 servings",
        "ingredients": [
            {"text": "2 cups flour", "quantity": "2", "unit": "cup"}
        ],
        "steps": [
            {"order": 1, "text": "Mix ingredients"}
        ]
    }
    assert validate_recipe_completeness(complete_recipe) == []
    
    # Minimal valid recipe - only title required
    minimal_recipe = {"title": "Simple Recipe"}
    assert validate_recipe_completeness(minimal_recipe) == []
    
    # Missing title
    recipe = complete_recipe.copy()
    recipe["title"] = ""
    issues = validate_recipe_completeness(recipe)
    assert any("title" in issue for issue in issues)
    
    # Invalid yield (empty string when provided)
    recipe = complete_recipe.copy()
    recipe["yield"] = ""
    issues = validate_recipe_completeness(recipe)
    assert any("Yield" in issue for issue in issues)
    
    # Invalid ingredients (not a list)
    recipe = {"title": "Test", "ingredients": "not a list"}
    issues = validate_recipe_completeness(recipe)
    assert any("Ingredients must be a list" in issue for issue in issues)
    
    # Invalid ingredient
    recipe = complete_recipe.copy()
    recipe["ingredients"] = [{"text": ""}]
    issues = validate_recipe_completeness(recipe)
    assert any("Ingredient 1" in issue for issue in issues)
    
    # Invalid steps (not a list)
    recipe = {"title": "Test", "steps": "not a list"}
    issues = validate_recipe_completeness(recipe)
    assert any("Steps must be a list" in issue for issue in issues)
    
    # Invalid step order
    recipe = complete_recipe.copy()
    recipe["steps"] = [{"order": 0, "text": "Invalid order"}]
    issues = validate_recipe_completeness(recipe)
    assert any("order" in issue for issue in issues)
    
    # Empty ingredients and steps arrays should be valid
    recipe = {"title": "Minimal Recipe", "ingredients": [], "steps": []}
    issues = validate_recipe_completeness(recipe)
    assert issues == []  # No validation errors
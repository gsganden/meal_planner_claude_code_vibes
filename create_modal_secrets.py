#!/usr/bin/env python3
"""
Create Modal secrets from .env file
"""
import os
import subprocess
from pathlib import Path
from dotenv import dotenv_values

def create_modal_secrets():
    # Load .env file
    env_path = Path(".env")
    if not env_path.exists():
        print("❌ .env file not found. Please create one from .env.example")
        return
    
    # Load environment variables
    config = dotenv_values(".env")
    
    # Filter out empty values and DATABASE_URL (Modal sets this automatically)
    secrets = {k: v for k, v in config.items() if v and k != "DATABASE_URL"}
    
    # Build the modal command
    cmd = ["modal", "secret", "create", "recipe-chat-secrets"]
    
    for key, value in secrets.items():
        # Remove quotes if present
        value = value.strip("'\"")
        cmd.append(f"{key}={value}")
    
    print("🔐 Creating Modal secrets...")
    print(f"📝 Keys: {', '.join(secrets.keys())}")
    
    try:
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode == 0:
            print("✅ Modal secrets created successfully!")
        else:
            print(f"❌ Failed to create secrets: {result.stderr}")
            if "already exists" in result.stderr:
                print("\n💡 To update existing secrets, first delete them:")
                print("   modal secret delete recipe-chat-secrets")
                print("   Then run this script again.")
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    create_modal_secrets()
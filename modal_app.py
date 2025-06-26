import modal
from modal import App, Image, Volume, asgi_app, Secret
import os

# Create Modal app
app = App("recipe-chat-assistant")

# Define the container image with all dependencies
image = (
    Image.debian_slim(python_version="3.11")
    .pip_install_from_requirements("requirements.txt")
    .copy_local_dir("src", "/app/src")
    .copy_local_dir("prompts", "/app/prompts")
    .copy_local_file("src/main.py", "/app/src/main.py")
)

# Create volume for SQLite database persistence
volume = Volume.from_name("recipe-data-volume", create_if_missing=True)


@app.function(
    image=image,
    secrets=[Secret.from_name("recipe-chat-secrets")],
    volumes={"/data": volume},
    cpu=1,
    memory=512,
    concurrency_limit=100,
    container_idle_timeout=300,
)
@asgi_app()
def fastapi_app():
    import sys
    sys.path.append('/app')
    # Set database URL to use Modal volume
    os.environ["DATABASE_URL"] = "sqlite+aiosqlite:////data/production.db"
    
    from src.main import app
    return app


@app.function(
    image=image,
    secrets=[Secret.from_name("recipe-chat-secrets")],
    volumes={"/data": volume},
    timeout=300,
)
async def init_deployment():
    """Initialize database tables on deployment"""
    import os
    import sys
    sys.path.append('/app')
    os.environ["DATABASE_URL"] = "sqlite+aiosqlite:////data/production.db"
    
    from src.db.database import init_db
    print("Initializing database...")
    await init_db()
    print("Database initialized successfully!")


if __name__ == "__main__":
    # For local testing
    import asyncio
    asyncio.run(init_deployment())
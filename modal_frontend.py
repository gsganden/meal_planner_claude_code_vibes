import modal
from modal import App, Mount, asgi_app
import os
import subprocess

# Create Modal app for frontend
app = App("recipe-chat-frontend")

# Define the container image with Node.js
image = (
    modal.Image.debian_slim(python_version="3.11")
    .run_commands(
        "apt-get update",
        "apt-get install -y curl",
        "curl -fsSL https://deb.nodesource.com/setup_20.x | bash -",
        "apt-get install -y nodejs",
    )
    .copy_local_dir("frontend_app", "/app/frontend_app")
    .run_commands(
        "cd /app/frontend_app && npm install",
        "cd /app/frontend_app && npm run build",
    )
)


@app.function(
    image=image,
    mounts=[Mount.from_local_dir("frontend_app/dist", remote_path="/app/dist")],
    cpu=0.25,
    memory=256,
    concurrency_limit=100,
    container_idle_timeout=300,
)
@asgi_app()
def serve_frontend():
    """Serve the built frontend files"""
    from fastapi import FastAPI
    from fastapi.staticfiles import StaticFiles
    from fastapi.responses import FileResponse
    
    app = FastAPI()
    
    # Serve static files
    app.mount("/assets", StaticFiles(directory="/app/dist/assets"), name="assets")
    
    # Serve index.html for all routes (SPA routing)
    @app.get("/{full_path:path}")
    async def serve_spa(full_path: str):
        # Always return index.html for client-side routing
        return FileResponse("/app/dist/index.html")
    
    return app


# Alternative: Use Modal's static file serving (simpler but less flexible)
@app.function(
    image=modal.Image.debian_slim()
    .run_commands(
        "apt-get update",
        "apt-get install -y python3-pip",
        "pip install aiofiles",
    ),
    mounts=[Mount.from_local_dir("frontend_app/dist", remote_path="/dist")],
    cpu=0.25,
    memory=256,
    concurrency_limit=100,
    allow_concurrent_inputs=100,
)
@modal.web_endpoint(method="GET", label="recipe-chat-frontend")
def serve_static(path: str = ""):
    """Simple static file server"""
    import mimetypes
    
    if not path or path.endswith("/"):
        path = "index.html"
    
    file_path = f"/dist/{path}"
    
    # Handle client-side routing - return index.html for non-asset paths
    if not os.path.exists(file_path) and not path.startswith("assets/"):
        file_path = "/dist/index.html"
    
    if not os.path.exists(file_path):
        return {"error": "File not found"}, 404
    
    # Determine content type
    content_type, _ = mimetypes.guess_type(file_path)
    if content_type is None:
        content_type = "application/octet-stream"
    
    with open(file_path, "rb") as f:
        content = f.read()
    
    return modal.Response(
        content,
        media_type=content_type,
        headers={
            "Cache-Control": "public, max-age=3600" if path.startswith("assets/") else "no-cache"
        }
    )
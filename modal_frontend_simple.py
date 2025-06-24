"""
Deploy React frontend to Modal as static files
"""
import modal
import os
import mimetypes

app = modal.App("recipe-chat-frontend")

# Mount the built frontend files
frontend_mount = modal.Mount.from_local_dir(
    "frontend_app/dist",
    remote_path="/dist",
)


@app.function(
    mounts=[frontend_mount],
    cpu=0.25,
    memory=256,
    container_idle_timeout=300,
    concurrency_limit=100,
)
@modal.web_endpoint(method="GET", label="recipe-chat-frontend")
def serve(path: str = ""):
    """Serve static files with client-side routing support"""
    
    # Default to index.html
    if not path or path == "/":
        path = "index.html"
    
    # Construct file path
    file_path = f"/dist/{path}"
    
    # For client-side routing: if file doesn't exist and it's not an asset,
    # serve index.html
    if not os.path.exists(file_path):
        # Check if it's an asset request
        if not any(path.startswith(prefix) for prefix in ["assets/", "favicon", "."]):
            file_path = "/dist/index.html"
    
    # Return 404 if file still doesn't exist
    if not os.path.exists(file_path):
        return modal.Response(
            "File not found",
            status_code=404,
            media_type="text/plain"
        )
    
    # Read file content
    with open(file_path, "rb") as f:
        content = f.read()
    
    # Determine content type
    content_type, _ = mimetypes.guess_type(file_path)
    if content_type is None:
        if file_path.endswith(".js"):
            content_type = "application/javascript"
        elif file_path.endswith(".css"):
            content_type = "text/css"
        elif file_path.endswith(".html"):
            content_type = "text/html"
        else:
            content_type = "application/octet-stream"
    
    # Set cache headers
    headers = {}
    if path.startswith("assets/"):
        # Cache assets for 1 year (they have hashed filenames)
        headers["Cache-Control"] = "public, max-age=31536000, immutable"
    else:
        # Don't cache HTML files
        headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    
    return modal.Response(
        content,
        media_type=content_type,
        headers=headers
    )


if __name__ == "__main__":
    # For local testing
    print("Deploy with: modal deploy modal_frontend_simple.py")
    print("After deployment, your frontend will be available at:")
    print("https://<your-username>--recipe-chat-frontend-serve.modal.run")
# File Upload Flow (v0.1)

> **Purpose**: Define how users upload files (PDFs, images, videos) for recipe import, including security and storage considerations.

---

## 1. Upload Methods

### 1.1 Direct Upload to API
For files ≤25MB (security limit):

```
1. Client selects file
2. Client uploads to /v1/files/upload
3. API validates file type and size
4. API stores in temporary storage (S3)
5. API returns file token
6. Client uses token in import request
```

### 1.2 Pre-signed URL Upload
For larger files or better performance:

```
1. Client requests upload URL via /v1/files/upload-url
2. API generates pre-signed S3 URL (1 hour expiry)
3. Client uploads directly to S3
4. Client notifies API via /v1/files/confirm-upload
5. API validates and returns file token
```

## 2. API Endpoints

### 2.1 Direct Upload
```yaml
POST /v1/files/upload
Content-Type: multipart/form-data

Parameters:
  file: binary file data
  
Response 200:
{
  "file_token": "ft_abc123...",
  "expires_at": "2025-06-23T12:00:00Z"
}
```

### 2.2 Pre-signed URL Request
```yaml
POST /v1/files/upload-url
Content-Type: application/json

Body:
{
  "filename": "recipe.pdf",
  "content_type": "application/pdf",
  "size": 5242880
}

Response 200:
{
  "upload_url": "https://s3.amazonaws.com/...",
  "file_key": "uploads/user123/abc456.pdf",
  "expires_at": "2025-06-23T12:00:00Z"
}
```

### 2.3 Upload Confirmation
```yaml
POST /v1/files/confirm-upload
Content-Type: application/json

Body:
{
  "file_key": "uploads/user123/abc456.pdf"
}

Response 200:
{
  "file_token": "ft_abc123...",
  "expires_at": "2025-06-23T12:00:00Z"
}
```

## 3. File Token Usage

File tokens are used in import requests:

```json
{
  "source_type": "pdf",
  "source_ref": "ft_abc123..."
}
```

## 4. Security & Validation

### 4.1 File Type Validation
Allowed MIME types:
- `application/pdf` - Recipe PDFs
- `image/jpeg`, `image/png`, `image/webp` - Recipe photos
- `video/mp4`, `video/quicktime` - Cooking videos

### 4.2 Size Limits
- Direct upload: 25MB max
- Pre-signed upload: 100MB max
- Security scan on all uploads

### 4.3 Content Validation
- Magic byte verification (not just extension)
- Virus scanning (if available)
- No executable file types allowed

## 5. Storage Strategy

### 5.1 Temporary Storage
- Files stored with user-scoped prefix: `uploads/{user_id}/{uuid}.{ext}`
- 24-hour TTL for unused files
- Cleanup job removes expired files

### 5.2 File Token Format
```
ft_{base64(user_id:file_key:expires_at:signature)}
```

## 6. Import Integration

When import worker processes a file token:

```python
def process_file_token(token: str) -> bytes:
    # Decode and validate token
    user_id, file_key, expires_at, signature = decode_token(token)
    
    # Check expiry and signature
    if expires_at < now() or not verify_signature(signature):
        raise InvalidTokenError()
    
    # Download from S3
    return s3_client.get_object(file_key)
```

## 7. Error Handling

| Error | HTTP Code | Description |
|-------|-----------|-------------|
| `file_too_large` | 413 | File exceeds size limit |
| `unsupported_type` | 415 | File type not allowed |
| `upload_failed` | 500 | S3 upload error |
| `token_expired` | 410 | File token expired |
| `token_invalid` | 400 | Malformed or invalid token |

## 8. Rate Limits

- 10 uploads per hour per user
- 100MB total per hour per user
- Token generation limited to 20/hour

---

*End of File Upload Flow v0.1*
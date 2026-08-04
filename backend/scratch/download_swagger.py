import os
import urllib.request

static_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "app", "static"))
os.makedirs(static_dir, exist_ok=True)

files = {
    "swagger-ui-bundle.js": "https://cdn.jsdelivr.net/npm/swagger-ui-dist@5.9.0/swagger-ui-bundle.js",
    "swagger-ui.css": "https://cdn.jsdelivr.net/npm/swagger-ui-dist@5.9.0/swagger-ui.css",
    "favicon-32x32.png": "https://cdn.jsdelivr.net/npm/swagger-ui-dist@5.9.0/favicon-32x32.png"
}

print(f"Downloading Swagger UI assets into: {static_dir}")
for name, url in files.items():
    dest = os.path.join(static_dir, name)
    if os.path.exists(dest):
        print(f"{name} already exists, skipping.")
        continue
    try:
        print(f"Downloading {url}...")
        urllib.request.urlretrieve(url, dest)
        print(f"Successfully downloaded {name} ({os.path.getsize(dest)} bytes)")
    except Exception as e:
        print(f"Failed to download {name}: {e}")

print("Done.")

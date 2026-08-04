import os
import sys

# Adjust path to find app
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.main import app

try:
    print("Generating OpenAPI schema...")
    schema = app.openapi()
    print("SUCCESS: OpenAPI schema generated successfully!")
    print(f"Total paths: {len(schema.get('paths', {}))}")
except Exception as e:
    import traceback
    print("\nERROR generating OpenAPI schema:")
    traceback.print_exc()

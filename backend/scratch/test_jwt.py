import os
import sys

# Adjust path to find app
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.core.config import settings
from app.services.token_service import TokenService
from jose import jwt, JWTError

print("Secret key:", settings.SECRET_KEY)
print("Algorithm:", settings.JWT_ALGORITHM)

token = TokenService.create_access_token("123", "admin@example.com", "Admin")
print("Generated token:", token)

try:
    decoded = TokenService.decode_token(token)
    print("Decoded token successfully:", decoded)
except Exception as e:
    import traceback
    print("Failed to decode token:")
    traceback.print_exc()

import requests
import sys

API_URL = "http://127.0.0.1:8000/api/v1"

# 1. Login with seeded admin
payload = {
    "email": "admin@example.com",
    "password": "password123"
}

print("Attempting login...")
resp = requests.post(f"{API_URL}/auth/login", json=payload)
print("Login status:", resp.status_code)
if resp.status_code != 200:
    print("Login response:", resp.text)
    sys.exit(1)

data = resp.json()
token = data["access_token"]
print("Access token retrieved:", token[:20] + "...")

# 2. Query /users/me
headers = {
    "Authorization": f"Bearer {token}"
}
print("\nQuerying /users/me...")
me_resp = requests.get(f"{API_URL}/users/me", headers=headers)
print("Status code:", me_resp.status_code)
print("Response body:", me_resp.text)

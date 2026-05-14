"""
Run this script to get the Mercado Livre authorization URL (with PKCE).
After authorizing, the app will save your tokens automatically via /meli/callback.
"""
import base64
import hashlib
import os
import secrets
from pathlib import Path
from urllib.parse import urlencode

from dotenv import load_dotenv

load_dotenv(Path(__file__).parent / ".env")

CLIENT_ID = os.getenv("MELI_CLIENT_ID", "")
REDIRECT_URI = os.getenv("MELI_REDIRECT_URI", "http://localhost:8000/meli/callback")
AUTH_BASE = "https://auth.mercadolivre.com.br/authorization"
VERIFIER_FILE = Path(__file__).parent / ".meli_code_verifier"

# Generate PKCE code_verifier and code_challenge
code_verifier = secrets.token_urlsafe(64)
digest = hashlib.sha256(code_verifier.encode()).digest()
code_challenge = base64.urlsafe_b64encode(digest).rstrip(b"=").decode()

# Persist verifier so the callback endpoint can read it
VERIFIER_FILE.write_text(code_verifier)

params = {
    "response_type": "code",
    "client_id": CLIENT_ID,
    "redirect_uri": REDIRECT_URI,
    "code_challenge": code_challenge,
    "code_challenge_method": "S256",
}

url = f"{AUTH_BASE}?{urlencode(params)}"

print("\n=== Mercado Livre OAuth Setup ===\n")
print("1. Make sure the app is running:  uvicorn app.main:app --reload --port 8000")
print(f"2. Make sure this redirect URI is configured in the MELI Developer Portal:")
print(f"   {REDIRECT_URI}\n")
print("3. Open this URL in your browser:\n")
print(f"   {url}\n")
print("4. Log in and authorize the app.")
print("5. You'll be redirected — tokens are saved automatically to .env\n")

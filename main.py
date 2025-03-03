from fastapi import FastAPI, Query
from datetime import datetime, timedelta
import random, string
import redis
import requests
import os
from dotenv import load_dotenv

# Load .env
load_dotenv()

# Redis Upstash Credentials
REDIS_URL = os.getenv("REDIS_URL")
REDIS_TOKEN = os.getenv("REDIS_TOKEN")
WEBHOOK_URL = os.getenv("WEBHOOK_URL")

# Connect to Redis
redis_client = redis.Redis.from_url(REDIS_URL, password=REDIS_TOKEN, ssl=True)

app = FastAPI()

def generate_key():
    return ''.join(random.choices(string.ascii_letters + string.digits, k=32))

def get_expiry_seconds(expired_param: str):
    if expired_param.endswith("d"):
        return int(expired_param[:-1]) * 86400
    elif expired_param.endswith("w"):
        return int(expired_param[:-1]) * 604800
    elif expired_param.endswith("m"):
        return int(expired_param[:-1]) * 2592000
    return None

def send_webhook(title, description, color, key, expired_unix):
    """Kirim log ke Discord Webhook"""
    embed = {
        "title": title,
        "description": description,
        "color": color,
        "fields": [
            {"name": "🔑 Key", "value": f"```{key}```", "inline": False},
            {"name": "⏳ Expired", "value": f"<t:{expired_unix}:F> (<t:{expired_unix}:R>)", "inline": False}
        ],
        "footer": {"text": "Key System Logs"},
        "timestamp": datetime.utcnow().isoformat()
    }
    data = {"embeds": [embed]}
    requests.post(WEBHOOK_URL, json=data)

@app.get("/generate")
async def generate(expired: str = Query(None, description="Expiration time, e.g., 1d, 1w, 1m")):
    if not expired:
        return {"status": "error", "message": "Please provide expiration parameter"}

    expiry_seconds = get_expiry_seconds(expired)
    if not expiry_seconds:
        return {"status": "error", "message": "Invalid expiration format"}

    key = generate_key()
    expired_unix = int(datetime.utcnow().timestamp()) + expiry_seconds
    redis_client.setex(key, expiry_seconds, "valid")

    # Kirim Webhook Log
    send_webhook(
        title="✅ Key Generated",
        description="A new key has been created!",
        color=0x00FF00,  # Hijau
        key=key,
        expired_unix=expired_unix
    )

    return {"status": "success", "result": key, "expired": f"{expiry_seconds // 3600} hours"}

@app.get("/check")
async def check(key: str = Query(..., description="Key to check")):
    if not redis_client.exists(key):
        return {"status": "invalid key", "key": key}

    ttl_seconds = redis_client.ttl(key)
    if ttl_seconds <= 0:
        # Log Key Expired
        send_webhook(
            title="❌ Key Expired",
            description="A key was checked but has expired.",
            color=0xFF0000,  # Merah
            key=key,
            expired_unix=int(datetime.utcnow().timestamp())
        )
        return {"status": "key expired", "key": key}

    expired_unix = int(datetime.utcnow().timestamp()) + ttl_seconds
    return {"status": "success", "key": key, "expired": f"<t:{expired_unix}:F> (<t:{expired_unix}:R>)"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)

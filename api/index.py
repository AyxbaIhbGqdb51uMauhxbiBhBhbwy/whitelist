from fastapi import FastAPI, Query
from datetime import datetime, timedelta
import random, string

app = FastAPI()

# Database sementara untuk menyimpan key
keys_db = {}

def generate_key():
    return ''.join(random.choices(string.ascii_letters + string.digits, k=32))

def get_expiry_time(expired_param: str):
    now = datetime.utcnow()
    if expired_param.endswith("d"):
        return now + timedelta(days=int(expired_param[:-1]))
    elif expired_param.endswith("w"):
        return now + timedelta(weeks=int(expired_param[:-1]))
    elif expired_param.endswith("m"):
        return now + timedelta(days=int(expired_param[:-1]) * 30)
    return None

def cleanup_expired_keys():
    now = datetime.utcnow()
    expired_keys = [key for key, exp in keys_db.items() if exp < now]
    for key in expired_keys:
        del keys_db[key]

@app.get("/generate")
async def generate(expired: str = Query(None, description="Expiration time, e.g., 1d, 1w, 1m")):
    if not expired:
        return {"status": "Pls Provide Expired Params"}
    
    expiry_time = get_expiry_time(expired)
    if not expiry_time:
        return {"status": "error", "message": "Invalid expiration format"}
    
    key = generate_key()
    keys_db[key] = expiry_time
    hours_left = (expiry_time - datetime.utcnow()).total_seconds() / 3600
    
    return {"status": "success", "result": key, "expired": f"{hours_left:.2f} hours"}

@app.get("/check")
async def check(key: str = Query(..., description="Key to check")):
    cleanup_expired_keys()
    
    if key not in keys_db:
        return {"status": "invalid key", "key": key}
    
    expiry_time = keys_db[key]
    hours_left = (expiry_time - datetime.utcnow()).total_seconds() / 3600
    
    if expiry_time < datetime.utcnow():
        del keys_db[key]
        return {"status": "key expired", "key": key}
    
    return {"status": "success", "key": key, "expired": f"{hours_left:.2f} hours"}

@app.get("/data")
async def data():
    cleanup_expired_keys()
    return {"Count": len(keys_db), "keys": {key: exp.strftime('%Y-%m-%d %H:%M:%S') for key, exp in keys_db.items()}}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)

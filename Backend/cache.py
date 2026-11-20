import os
from dotenv import load_dotenv
import redis

load_dotenv()

try:
    redis_client = redis.Redis.from_url(
        os.getenv("REDIS_URL", "redis://localhost:6379/0"),
        decode_responses=True,
    )
    redis_client.ping()
    print("[OK] Redis connected successfully")
except Exception as e:
    redis_client = None
    print(f"[WARNING] Could not connect to Redis: {e}")

def get_redis():
    return redis_client

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from fastapi.responses import RedirectResponse
import hashlib
import os
import redis


app = FastAPI(title="Kubernetes URL Shortener")


redis_host = os.getenv("REDIS_HOST", "localhost")
redis_port = int(os.getenv("REDIS_PORT", "6379"))
redis_password = os.getenv("REDIS_PASSWORD")

r = redis.Redis(
    host=redis_host,
    port=redis_port,
    password=redis_password,
    decode_responses=True
)


class URLRequest(BaseModel):
    url: str


@app.get("/health")
def health():
    try:
        r.ping()
        return {"status": "healthy"}
    except redis.RedisError:
        raise HTTPException(
            status_code=503,
            detail="Redis unavailable"
        )


@app.post("/shorten")
def shorten_url(request: URLRequest):

    short_code = hashlib.md5(
        request.url.encode()
    ).hexdigest()[:6]

    r.set(short_code, request.url)

    return {
        "short_code": short_code,
        "url": request.url
    }


@app.get("/{short_code}")
def redirect_url(short_code: str):

    url = r.get(short_code)

    if url is None:
        raise HTTPException(
            status_code=404,
            detail="URL not found"
        )

    return RedirectResponse(url=url)
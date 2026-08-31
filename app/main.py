from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from fastapi.responses import RedirectResponse
import hashlib


app = FastAPI(title="Kubernetes URL Shortener")


class URLRequest(BaseModel):
    url: str


urls = {}


@app.get("/health")
def health():
    return {"status": "healthy"}


@app.post("/shorten")
def shorten_url(request: URLRequest):
    short_code = hashlib.md5(
        request.url.encode()
    ).hexdigest()[:6]

    urls[short_code] = request.url

    return {
        "short_code": short_code,
        "url": request.url
    }


@app.get("/{short_code}")
def redirect_url(short_code: str):
    if short_code not in urls:
        raise HTTPException(
            status_code=404,
            detail="URL not found"
        )

    return RedirectResponse(url=urls[short_code])
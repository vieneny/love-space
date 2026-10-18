"""Restricted, temporary preview proxy; run on 127.0.0.1 with access logs off.

This module deliberately does not import the application or load its .env file.
PREVIEW_API_UPSTREAM must be an explicit RFC1918 IPv4 HTTP origin. It is never
selected from a request. Only the app API and health endpoint are exposed.
"""

from contextlib import asynccontextmanager
from ipaddress import IPv4Address, IPv4Network
import logging
import os
import re

import httpx
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse, Response
from starlette.requests import ClientDisconnect


APP_PREFIX = "/api/v1/app/"
DEV_LOGIN = APP_PREFIX + "auth/dev-login"
NORMAL_LIMIT = 256 * 1024
UPLOAD_LIMIT = 12 * 1024 * 1024
METHODS = ["GET", "HEAD", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"]
PRIVATE_NETWORKS = tuple(IPv4Network(value) for value in
                         ("10.0.0.0/8", "172.16.0.0/12", "192.168.0.0/16"))
HOP_HEADERS = {
    b"connection", b"keep-alive", b"proxy-authenticate", b"proxy-authorization",
    b"proxy-connection", b"te", b"trailer", b"transfer-encoding", b"upgrade",
}


def validate_upstream(value: str) -> str:
    """Accept a canonical private IPv4 origin, without DNS or URL credentials."""
    match = re.fullmatch(r"http://([0-9.]+)(?::([0-9]{1,5}))?/?", value)
    if match is None:
        raise ValueError("PREVIEW_API_UPSTREAM requires a private IPv4 HTTP origin")
    try:
        address = IPv4Address(match[1])
    except ValueError:
        raise ValueError("PREVIEW_API_UPSTREAM requires a private IPv4 HTTP origin") from None
    if not any(address in network for network in PRIVATE_NETWORKS):
        raise ValueError("PREVIEW_API_UPSTREAM must be inside RFC1918 address space")
    port = match[2]
    if port is not None and (not 1 <= int(port) <= 65535 or str(int(port)) != port):
        raise ValueError("PREVIEW_API_UPSTREAM has an invalid port")
    return value.rstrip("/")


def filtered_headers(raw: list[tuple[bytes, bytes]], *, request: bool) -> list[tuple[bytes, bytes]]:
    blocked = set(HOP_HEADERS)
    for name, value in raw:
        if name.lower() == b"connection":
            blocked.update(item.strip().lower() for item in value.split(b","))
    # httpx decodes response bodies; Response supplies their new Content-Length.
    blocked.add(b"content-length")
    if request:
        blocked.update({b"host", b"forwarded", b"x-real-ip"})
    else:
        blocked.add(b"content-encoding")
    return [(name, value) for name, value in raw
            if name.lower() not in blocked
            and not (request and name.lower().startswith(b"x-forwarded-"))]


def allowed_path(scope: dict) -> bool:
    path = scope["path"]
    # Reject all escaped paths rather than normalizing them into another route.
    # API identifiers are ASCII; encoded query values (including media tokens)
    # are passed separately and are not affected by this check.
    raw = scope.get("raw_path", b"")
    if not re.fullmatch(rb"/[A-Za-z0-9/_~.-]*", raw) or raw.decode("ascii") != path:
        return False
    if "//" in path or any(part in {".", ".."} for part in path.split("/")):
        return False
    if path == "/health":
        return True
    if not path.startswith(APP_PREFIX) or path == APP_PREFIX:
        return False
    return path.rstrip("/") != DEV_LOGIN and not path.startswith(DEV_LOGIN + "/")


def error(status: int, detail: str) -> JSONResponse:
    return JSONResponse({"detail": detail}, status_code=status,
                        headers={"Cache-Control": "no-store"})


def create_app(upstream: str | None = None,
               transport: httpx.AsyncBaseTransport | None = None) -> FastAPI:
    @asynccontextmanager
    async def lifespan(app: FastAPI):
        origin = validate_upstream(upstream if upstream is not None else
                                   os.environ.get("PREVIEW_API_UPSTREAM", ""))
        # httpx INFO request logs include the complete URL, including signed
        # media queries. Keep both HTTP client libraries out of verbose logs.
        client_loggers = [logging.getLogger(name) for name in ("httpx", "httpcore")]
        previous_levels = [logger.level for logger in client_loggers]
        for logger in client_loggers:
            logger.setLevel(logging.WARNING)
        try:
            async with httpx.AsyncClient(
                transport=transport, trust_env=False, follow_redirects=False,
                timeout=httpx.Timeout(30, connect=5, pool=5),
                limits=httpx.Limits(max_connections=20, max_keepalive_connections=10),
            ) as client:
                app.state.upstream = origin
                app.state.client = client
                yield
        finally:
            for logger, level in zip(client_loggers, previous_levels):
                logger.setLevel(level)

    app = FastAPI(title="Restricted development preview", docs_url=None,
                  redoc_url=None, openapi_url=None, lifespan=lifespan)

    @app.middleware("http")
    async def route_boundary(request: Request, call_next):
        if not allowed_path(request.scope):
            return error(404, "Not found")
        if request.method not in METHODS or (request.url.path == "/health"
                                               and request.method not in {"GET", "HEAD"}):
            return error(405, "Method not allowed")
        return await call_next(request)

    @app.api_route("/{path:path}", methods=METHODS)
    async def proxy(request: Request, path: str):
        is_upload = (request.method == "POST" and request.url.path == APP_PREFIX + "media"
                     and request.headers.get("content-type", "").lower().startswith("multipart/form-data;"))
        limit = UPLOAD_LIMIT if is_upload else NORMAL_LIMIT
        lengths = request.headers.getlist("content-length")
        if lengths:
            if len(lengths) != 1 or not re.fullmatch(r"[0-9]+", lengths[0]):
                return error(400, "Invalid content length")
            if len(lengths[0]) > 10 or int(lengths[0]) > limit:
                return error(413, "Request body too large")
        body = bytearray()
        try:
            async for chunk in request.stream():
                if len(body) + len(chunk) > limit:
                    return error(413, "Request body too large")
                body.extend(chunk)
        except ClientDisconnect:
            return error(400, "Incomplete request body")
        if lengths and int(lengths[0]) != len(body):
            return error(400, "Invalid content length")
        target = httpx.URL(request.app.state.upstream + request.url.path).copy_with(
            query=request.scope.get("query_string", b""))
        try:
            result = await request.app.state.client.request(
                request.method, target, content=bytes(body),
                headers=filtered_headers(request.headers.raw, request=True))
        except httpx.TimeoutException:
            # Exception strings can contain private paths and signed queries.
            return error(504, "Preview upstream timed out")
        except httpx.HTTPError:
            return error(502, "Preview upstream unavailable")
        response = Response(content=result.content, status_code=result.status_code)
        response.raw_headers = filtered_headers(result.headers.raw, request=False)
        response.raw_headers.append((b"content-length", str(len(result.content)).encode("ascii")))
        return response

    return app


app = create_app()

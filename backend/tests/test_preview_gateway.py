import gzip
import logging

from fastapi.testclient import TestClient
import httpx
import pytest

from app.preview_gateway import create_app, NORMAL_LIMIT, UPLOAD_LIMIT, validate_upstream


@pytest.mark.parametrize("origin", [
    "", "http://example.com", "https://192.168.1.100", "http://127.0.0.1:18101",
    "http://8.8.8.8", "http://169.254.169.254", "http://172.32.0.1",
    "http://[::1]", "http://user:pass@192.168.1.100", "http://192.168.1.100/path",
    "http://192.168.1.100?target=http://8.8.8.8", "http://192.168.1.100#fragment",
    "http://192.168.001.100", "http://3232235876", "http://192.168.1.100:0",
    "http://192.168.1.100:65536", "http://192.168.1.100:018101", " http://192.168.1.100",
])
def test_non_private_or_non_origin_config_fails_closed(origin):
    with pytest.raises(ValueError, match="PREVIEW_API_UPSTREAM"):
        with TestClient(create_app(origin)):
            pass


def test_no_upstream_default(monkeypatch):
    monkeypatch.delenv("PREVIEW_API_UPSTREAM", raising=False)
    with pytest.raises(ValueError, match="PREVIEW_API_UPSTREAM"):
        with TestClient(create_app()):
            pass
    for origin in ["http://10.0.0.1", "http://172.16.0.1:8000/", "http://192.168.1.100:18101"]:
        assert validate_upstream(origin) == origin.rstrip("/")


def gateway(handler):
    return TestClient(create_app("http://192.168.1.100:18101", httpx.MockTransport(handler)))


def test_forbidden_routes_never_reach_upstream():
    def no_upstream(request):
        pytest.fail("A rejected request reached the upstream")

    with gateway(no_upstream) as client:
        for path in ["/", "/docs", "/redoc", "/openapi.json", "/ready", "/.env",
                     "/api/v1/admin/settings", "/api/v1/admin/auth/login", "/api/v1/app",
                     "/api/v1/app/", "/api/v1/app/auth/dev-login",
                     "/api/v1/app/auth/dev-login/", "/api/v1/app/auth/dev-login/extra",
                     "/api/v1/app/auth/%64ev-login", "/api/v1/app/auth%2fdev-login",
                     "/api/v1/app/%2e%2e/admin/settings", "/api/v1/app//auth/dev-login",
                     "/api/v1/app/memories%5c..%5cauth%5cdev-login"]:
            assert client.post(path).status_code == 404, path
        assert client.request("TRACE", "/api/v1/app/me").status_code == 405
        assert client.post("/health").status_code == 405


def test_auth_override_query_body_status_and_headers_are_preserved():
    seen = []

    def upstream(request):
        seen.append(request)
        return httpx.Response(207, content=b'{"updated":true}', headers={
            "Content-Type": "application/json", "Cache-Control": "private, no-store",
            "X-App-Result": "kept", "Connection": "x-remove", "X-Remove": "hidden",
            "Keep-Alive": "timeout=20", "Proxy-Authenticate": "hidden",
        })

    with gateway(upstream) as client:
        response = client.post("/api/v1/app/memories/abc?token=a%2Bb%3D&scope=personal",
                               content=b'{"title":"new"}', headers={
                                   "Authorization": "Bearer synthetic-preview-token",
                                   "X-HTTP-Method-Override": "PATCH", "Content-Type": "application/json",
                                   "Connection": "x-remove", "X-Remove": "hidden",
                                   "Host": "untrusted.example", "X-Forwarded-Host": "untrusted.example",
                                   "X-Forwarded-For": "8.8.8.8", "Proxy-Authorization": "hidden",
                               })
    request = seen[0]
    assert len(seen) == 1
    assert str(request.url) == "http://192.168.1.100:18101/api/v1/app/memories/abc?token=a%2Bb%3D&scope=personal"
    assert request.method == "POST" and request.content == b'{"title":"new"}'
    assert request.headers["authorization"] == "Bearer synthetic-preview-token"
    assert request.headers["x-http-method-override"] == "PATCH"
    assert request.headers["host"] == "192.168.1.100:18101"
    for name in ["x-remove", "x-forwarded-host", "x-forwarded-for", "proxy-authorization"]:
        assert name not in request.headers
    assert response.status_code == 207 and response.content == b'{"updated":true}'
    assert response.headers["cache-control"] == "private, no-store"
    assert response.headers["x-app-result"] == "kept"
    assert response.headers["content-length"] == str(len(response.content))
    for name in ["connection", "x-remove", "keep-alive", "proxy-authenticate"]:
        assert name not in response.headers


def test_health_and_redirects_are_passed_without_following():
    calls = []

    def upstream(request):
        calls.append(request)
        if request.url.path == "/health":
            return httpx.Response(200, json={"status": "ok"})
        return httpx.Response(307, content=b"redirect", headers={"Location": "http://8.8.8.8/private"})

    with gateway(upstream) as client:
        assert client.get("/health").json() == {"status": "ok"}
        response = client.get("/api/v1/app/me", follow_redirects=False)
        assert response.status_code == 307 and response.content == b"redirect"
        assert response.headers["location"] == "http://8.8.8.8/private"
    assert len(calls) == 2


def test_decoded_response_length_and_encoding_are_consistent():
    plain = b"private image response" * 50

    def upstream(request):
        compressed = gzip.compress(plain)
        return httpx.Response(200, content=compressed, headers={
            "Content-Encoding": "gzip", "Content-Length": str(len(compressed)),
            "Content-Type": "image/png",
        })

    with gateway(upstream) as client:
        response = client.get("/api/v1/app/media/synthetic-token?token=signed")
        assert response.content == plain
        assert "content-encoding" not in response.headers
        assert response.headers["content-length"] == str(len(plain))


def test_declared_and_chunked_body_limits_reject_before_proxy():
    seen = []

    def upstream(request):
        seen.append(request)
        return httpx.Response(200, json={"bytes": len(request.content)})

    with gateway(upstream) as client:
        for headers in [{"Content-Length": str(NORMAL_LIMIT + 1)}, {"Content-Length": "invalid"},
                        [("Content-Length", "1"), ("Content-Length", "1")]]:
            response = client.post("/api/v1/app/memories", content=b"x", headers=headers)
            assert response.status_code in {400, 413}
        response = client.post("/api/v1/app/memories", content=iter([b"x" * NORMAL_LIMIT, b"x"]))
        assert response.status_code == 413
        assert client.post("/api/v1/app/memories", content=b"short",
                           headers={"Content-Length": "10"}).status_code == 400
        assert not seen
        assert client.post("/api/v1/app/memories", content=b"x" * NORMAL_LIMIT).status_code == 200
        assert len(seen) == 1


def test_large_body_allowance_is_only_for_multipart_media_uploads():
    seen = []

    def upstream(request):
        seen.append(request)
        return httpx.Response(201, json={"bytes": len(request.content)})

    with gateway(upstream) as client:
        payload = b"synthetic-image" * 30_000
        response = client.post("/api/v1/app/media", files={"file": ("image.png", payload, "image/png")})
        assert response.status_code == 201
        assert response.json()["bytes"] > NORMAL_LIMIT
        headers = {"Content-Type": "multipart/form-data; boundary=synthetic"}
        assert client.post("/api/v1/app/media", content=iter([b"x" * UPLOAD_LIMIT, b"x"]),
                           headers=headers).status_code == 413
        assert client.post("/api/v1/app/memories", content=payload, headers=headers).status_code == 413
        assert client.post("/api/v1/app/media", content=payload,
                           headers={"Content-Type": "application/json"}).status_code == 413
        assert len(seen) == 1


@pytest.mark.parametrize("failure,status", [(httpx.ConnectError, 502), (httpx.ReadTimeout, 504)])
def test_upstream_errors_do_not_disclose_signed_query(failure, status, caplog):
    secret = "synthetic-signed-token-do-not-log"
    caplog.set_level(logging.INFO)

    def unavailable(request):
        raise failure(str(request.url), request=request)

    with gateway(unavailable) as client:
        response = client.get("/api/v1/app/media/id?token=" + secret)
        assert response.status_code == status
        assert secret not in response.text
        assert secret not in caplog.text

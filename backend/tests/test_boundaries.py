from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta
from io import BytesIO
import os

from fastapi.testclient import TestClient
from PIL import Image
import pytest
from pydantic import ValidationError
from sqlalchemy import select

from app.config import Settings
from app.main import create_app
from app.models import Base, Invitation, now

A = "/api/v1/app"
B = "/api/v1/admin"


@pytest.fixture
def client(tmp_path):
    database_url = os.environ.get("LOVE_SPACE_TEST_DATABASE_URL", f"sqlite:///{tmp_path / 'test.db'}")
    if database_url.startswith("postgresql"):
        assert database_url.endswith("/love_space_backend_test"), "Only a dedicated disposable test database is allowed"
    settings = Settings(_env_file=None, environment="test", database_url=database_url,
                        media_root=tmp_path / "media", jwt_secret="test-secret-with-at-least-32-bytes",
                        admin_password="test-administrator-password", media_max_bytes=100_000)
    app = create_app(settings)
    if database_url.startswith("postgresql"):
        Base.metadata.drop_all(app.state.engine)
    with TestClient(app) as c:
        yield c


def login(c, identity):
    response = c.post(A + "/auth/dev-login", json={"identity": identity})
    assert response.status_code == 200, response.text
    data = response.json()
    return {"Authorization": "Bearer " + data["access_token"]}


def pair(c, a="alice", b="bob"):
    ah, bh = login(c, a), login(c, b)
    assert c.post(A + "/spaces", headers=ah, json={"title": a + "+" + b}).status_code == 200
    code = c.post(A + "/spaces/invitations", headers=ah).json()["code"]
    joined = c.post(A + "/spaces/join", headers=bh, json={"code": code})
    assert joined.status_code == 200, joined.text
    return ah, bh


def memory(c, h, **overrides):
    data = {"title": "Private title", "content": "Private diary", "occurred_on": "2024-02-29", "kind": "daily"}
    data.update(overrides)
    return c.post(A + "/memories", headers=h, json=data)


def photo(c, h):
    image = BytesIO()
    Image.new("RGB", (8, 8), "red").save(image, format="PNG")
    result = c.post(A + "/media", headers=h, files={"file": ("../unsafe.png", image.getvalue(), "image/png")})
    assert result.status_code == 200, result.text
    return result.json()


def test_two_spaces_private_and_shared_authorization(client):
    alice, bob = pair(client)
    carol, dave = pair(client, "carol", "dave")
    private = memory(client, alice).json()
    shared = memory(client, alice, visibility="shared").json()
    assert client.get(A + f"/memories/{private['id']}", headers=bob).status_code == 404
    assert client.get(A + f"/memories/{shared['id']}", headers=bob).status_code == 200
    for other in [carol, dave]:
        assert client.get(A + f"/memories/{shared['id']}", headers=other).status_code == 404
        assert client.patch(A + f"/memories/{shared['id']}", headers=other, json={"title": "hacked"}).status_code == 404
    assert client.get(A + "/memories?scope=shared", headers=bob).json()["total"] == 1
    assert client.get(A + "/memories?scope=personal", headers=bob).json()["total"] == 0
    assert client.patch(A + f"/memories/{shared['id']}", headers=bob, json={"title": "hacked"}).status_code == 403


def test_trip_and_media_parent_injection(client):
    alice, bob = pair(client)
    carol, dave = pair(client, "carol", "dave")
    foreign_trip = client.post(A + "/trips", headers=carol, json={"title": "Other trip", "visibility": "shared"}).json()
    assert memory(client, alice, visibility="shared", trip_id=foreign_trip["id"]).status_code == 404
    trip = client.post(A + "/trips", headers=alice, json={"title": "Shared trip", "visibility": "shared"}).json()
    assert memory(client, alice, trip_id=trip["id"]).status_code == 422
    foreign_photo = photo(client, carol)
    assert memory(client, alice, visibility="shared", photo_ids=[foreign_photo["id"]]).status_code == 404
    partner_photo = photo(client, bob)
    assert memory(client, alice, visibility="shared", photo_ids=[partner_photo["id"]]).status_code == 404
    private_trip = client.post(A + "/trips", headers=bob, json={"title": "Private trip"}).json()
    assert memory(client, alice, trip_id=private_trip["id"]).status_code == 404


def test_unbinding_revokes_existing_media_urls_and_preserves_authors(client):
    alice, bob = pair(client)
    p = photo(client, alice)
    shared = memory(client, alice, visibility="shared", photo_ids=[p["id"]]).json()
    b_record = client.get(A + f"/memories/{shared['id']}", headers=bob).json()
    old_url = b_record["photos"][0]["url"]
    assert client.get(old_url).status_code == 200
    assert client.get(old_url).headers["cache-control"] == "private, no-store"
    assert client.post(A + "/spaces/unbind", headers=bob).status_code == 200
    assert client.get(A + "/me", headers=alice).json()["space_id"] is None
    assert client.get(old_url).status_code == 404
    assert client.get(A + f"/memories/{shared['id']}", headers=bob).status_code == 404
    assert client.get(A + f"/memories/{shared['id']}", headers=alice).status_code == 200
    assert client.get(p["url"]).status_code == 200
    assert client.get(A + "/memories?scope=personal", headers=alice).json()["total"] == 1
    client.post(A + "/spaces", headers=alice, json={"title": "New relationship"})
    assert client.get(A + "/memories?scope=shared", headers=alice).json()["total"] == 0


def test_invitation_atomic_capacity_under_concurrency(client):
    alice = login(client, "alice")
    client.post(A + "/spaces", headers=alice, json={"title": "Two people"})
    code = client.post(A + "/spaces/invitations", headers=alice).json()["code"]
    entrants = [login(client, "entrant" + str(i)) for i in range(8)]
    def attempt(headers):
        return client.post(A + "/spaces/join", headers=headers, json={"code": code}).status_code
    with ThreadPoolExecutor(max_workers=8) as executor:
        statuses = list(executor.map(attempt, entrants))
    assert statuses.count(200) == 1, statuses
    assert statuses.count(409) == 7, statuses
    assert len(client.get(A + "/spaces/current", headers=alice).json()["members"]) == 2


def test_invitation_expiration_rotation_and_self_join(client):
    alice, bob = login(client, "alice"), login(client, "bob")
    client.post(A + "/spaces", headers=alice, json={"title": "Two people"})
    first = client.post(A + "/spaces/invitations", headers=alice).json()["code"]
    second = client.post(A + "/spaces/invitations", headers=alice).json()["code"]
    assert client.post(A + "/spaces/join", headers=bob, json={"code": first}).status_code == 409
    assert client.post(A + "/spaces/join", headers=alice, json={"code": second}).status_code == 409
    with client.app.state.sessions.begin() as db:
        for invite in db.scalars(select(Invitation)):
            invite.expires_at = now() - timedelta(seconds=1)
    assert client.post(A + "/spaces/join", headers=bob, json={"code": second}).status_code == 409


def test_question_answers_unlock_only_after_both_answer(client):
    alice, bob = pair(client)
    carol, dave = pair(client, "carol", "dave")
    q = client.get(A + "/interaction/today", headers=alice).json()
    assert q["my_answer"] is None and q["partner_answer"] is None
    result = client.post(A + "/interaction/answers", headers=alice, json={"question_id": q["id"], "answer": "secret"}).json()
    assert result["both_answered"] is False
    assert client.get(A + "/interaction/today", headers=bob).json()["partner_answer"] is None
    assert client.post(A + "/interaction/answers", headers=carol, json={"question_id": q["id"], "answer": "intruder"}).status_code == 404
    result = client.post(A + "/interaction/answers", headers=bob, json={"question_id": q["id"], "answer": "my answer"}).json()
    assert result["both_answered"] is True and result["partner_answer"] == "secret"
    assert client.get(A + "/interaction/today", headers=alice).json()["partner_answer"] == "my answer"
    client.post(A + "/spaces/unbind", headers=alice)
    assert client.get(A + "/interaction/today", headers=bob).status_code == 409


def test_habit_checkins_idempotent_and_scoped(client):
    alice, bob = pair(client)
    carol = login(client, "carol")
    h = client.post(A + "/habits", headers=alice, json={"title": "Walk together"}).json()
    route = A + f"/habits/{h['id']}/checkins"
    with ThreadPoolExecutor(max_workers=4) as ex:
        responses = list(ex.map(lambda _: client.post(route, headers=alice, json={}), range(4)))
    assert all(r.status_code == 200 for r in responses)
    assert len(client.get(A + "/habits", headers=bob).json()["items"][0]["checkins"]) == 1
    client.post(A + "/spaces", headers=carol, json={"title": "Other"})
    assert client.post(route, headers=carol, json={}).status_code == 404


def test_image_validation_and_file_token_binding(client):
    alice = login(client, "alice")
    assert client.post(A + "/media", headers=alice, files={"file": ("a.jpg", b"<svg>not an image</svg>", "image/jpeg")}).status_code == 415
    assert client.post(A + "/media", headers=alice, files={"file": ("a.jpg", b"a" * 100_001, "image/jpeg")}).status_code == 413
    p, q = photo(client, alice), photo(client, alice)
    assert client.get(p["url"].replace(p["id"], q["id"], 1)).status_code == 404
    assert client.get(A + "/media/" + p["id"]).status_code == 422
    assert client.get("/static/" + p["id"]).status_code == 404


def test_global_map_stats_repeat_visits_crs_and_date_filters(client):
    alice = login(client, "alice")
    place = {"name": "Cafe", "country_code": "pt", "city": "Lisbon", "latitude": 38.7,
             "longitude": -9.1, "coordinate_system": "wgs84", "timezone": "Europe/Lisbon"}
    first = memory(client, alice, place=place).json()
    assert first["place"]["coordinate_system"] == "wgs84"
    assert first["occurred_on"] == "2024-02-29"
    memory(client, alice, place=place, occurred_on="2025-03-01")
    memory(client, alice, place={"name": "Text location"})
    result = client.get(A + "/map/footprints", headers=alice).json()
    assert result["stats"] == {"countries": 1, "cities": 1, "places": 1, "visits": 2}
    assert client.get(A + "/map/footprints?year=2024", headers=alice).json()["stats"]["visits"] == 1
    assert client.get(A + "/map/footprints?scope=shared", headers=alice).json()["stats"]["visits"] == 0
    assert memory(client, alice, place={"name": "Invalid", "latitude": 22}).status_code == 422


def test_trip_delete_detaches_partner_memories(client):
    alice, bob = pair(client)
    trip = client.post(A + "/trips", headers=alice, json={"title": "Together", "visibility": "shared"}).json()
    m = memory(client, bob, trip_id=trip["id"], visibility="shared").json()
    assert client.patch(A + f"/trips/{trip['id']}", headers=alice, json={"visibility": "private"}).status_code == 409
    assert client.delete(A + f"/trips/{trip['id']}", headers=alice).status_code == 200
    assert client.get(A + f"/memories/{m['id']}", headers=bob).json()["trip_id"] is None


def test_admin_audience_and_metadata_privacy(client):
    alice = login(client, "alice")
    memory(client, alice, title="ULTRA SECRET TITLE", content="ULTRA SECRET BODY")
    assert client.get(B + "/overview", headers=alice).status_code == 401
    response = client.post(B + "/auth/login", json={"username": "admin", "password": "test-administrator-password"})
    admin = {"Authorization": "Bearer " + response.json()["access_token"]}
    assert client.get(A + "/me", headers=admin).status_code == 401
    rows = client.get(B + "/memories", headers=admin)
    assert "ULTRA SECRET" not in rows.text
    assert set(rows.json()["items"][0]) == {"id", "author_id", "space_id", "trip_id", "kind", "visibility", "occurred_on", "created_at", "photo_count"}
    settings = client.get(B + "/settings", headers=admin).json()
    assert not any("secret" in k or "password" in k for k in settings)
    assert client.get(B + "/audit-logs", headers=admin).json()["total"] >= 2


def test_wechat_never_falls_back_to_development(client):
    response = client.post(A + "/auth/wechat-login", json={"code": "fake"})
    assert response.status_code == 503


def test_production_rejects_development_and_weak_configuration(tmp_path):
    with pytest.raises(ValidationError):
        Settings(_env_file=None, environment="production")
    with pytest.raises(ValidationError):
        Settings(_env_file=None, environment="production", jwt_secret="x" * 32, admin_password="x" * 12,
                 database_url="postgresql+psycopg://localhost/unused", dev_login_enabled=True)
    settings = Settings(_env_file=None, environment="production", jwt_secret="x" * 32, admin_password="x" * 12,
                        database_url="postgresql+psycopg://localhost/unused", dev_login_enabled=False,
                        media_root=tmp_path)
    # No lifespan or database connection is needed to reject this endpoint.
    app = create_app(settings)
    response = TestClient(app).post(A + "/auth/dev-login", json={"identity": "intruder"})
    assert response.status_code == 404


def test_wechat_patch_override_preserves_edit_authorization(client):
    alice, bob = pair(client)
    shared = memory(client, alice, visibility="shared").json()
    route = A + f"/memories/{shared['id']}"
    override = {"X-HTTP-Method-Override": "PATCH"}
    edited = client.post(route, headers={**alice, **override}, json={"title": "WeChat edit"})
    assert edited.status_code == 200, edited.text
    assert edited.json()["title"] == "WeChat edit"
    assert client.post(route, headers={**bob, **override}, json={"title": "Unauthorized"}).status_code == 403
    assert client.post(route, headers=override, json={"title": "Anonymous"}).status_code == 401
    ordinary = client.patch(route, headers=alice, json={"title": "H5 edit"})
    assert ordinary.status_code == 200
    assert client.get(route, headers=alice).json()["title"] == "H5 edit"


def test_patch_override_is_limited_to_post_app_routes(client):
    alice = login(client, "alice")
    m = memory(client, alice).json()
    route = A + f"/memories/{m['id']}"
    # Other override verbs must never turn a POST into destructive operations.
    assert client.post(route, headers={**alice, "X-HTTP-Method-Override": "DELETE"}).status_code == 405
    assert client.post(route, headers={**alice, "X-HTTP-Method-Override": "GET"}).status_code == 405
    duplicate = list(alice.items()) + [("X-HTTP-Method-Override", "PATCH"), ("X-HTTP-Method-Override", "PATCH")]
    assert client.post(route, headers=duplicate, json={"title": "Duplicate header"}).status_code == 405
    # A non-POST request stays GET and returns the unchanged original record.
    assert client.get(route, headers={**alice, "X-HTTP-Method-Override": "PATCH"}).json()["title"] == m["title"]
    admin_response = client.post(B + "/auth/login", json={"username": "admin", "password": "test-administrator-password"})
    admin = {"Authorization": "Bearer " + admin_response.json()["access_token"]}
    q = client.post(B + "/questions", headers=admin, json={"text": "Original question"}).json()
    assert client.post(B + f"/questions/{q['id']}", headers={**admin, "X-HTTP-Method-Override": "PATCH"},
                       json={"text": "Must not change"}).status_code == 405
    saved_question = next(item for item in client.get(B + "/questions", headers=admin).json()["items"] if item["id"] == q["id"])
    assert saved_question["text"] == "Original question"
    cors = client.options(route, headers={"Origin": "http://127.0.0.1:15174", "Access-Control-Request-Method": "POST",
                                           "Access-Control-Request-Headers": "authorization,x-http-method-override,content-type"})
    assert cors.status_code == 200


def test_editing_archived_shared_records_never_implicitly_shares_with_new_partner(client):
    alice, bob = pair(client)
    image = photo(client, alice)
    old = memory(client, alice, visibility="shared", photo_ids=[image["id"]]).json()
    own_trip = client.post(A + "/trips", headers=alice, json={"title": "Old trip", "visibility": "shared"}).json()
    empty_trip = client.post(A + "/trips", headers=alice, json={"title": "Old empty trip", "visibility": "shared"}).json()
    partner_trip = client.post(A + "/trips", headers=bob, json={"title": "Partner old trip", "visibility": "shared"}).json()
    in_own_trip = memory(client, alice, visibility="shared", trip_id=own_trip["id"]).json()
    in_partner_trip = memory(client, alice, visibility="shared", trip_id=partner_trip["id"]).json()
    client.post(A + "/spaces/unbind", headers=alice)
    alice, carol = pair(client, "alice", "carol")
    for old_memory in [old, in_own_trip, in_partner_trip]:
        route = A + f"/memories/{old_memory['id']}"
        for patch in [{"title": "Edited archived memory"}, {"title": "Still archived", "visibility": "shared"}]:
            response = client.patch(route, headers=alice, json=patch)
            assert response.status_code == 200, response.text
            assert client.get(route, headers=carol).status_code == 404
    for trip in [own_trip, empty_trip]:
        route = A + f"/trips/{trip['id']}"
        for patch in [{"title": "Edited archived trip"}, {"title": "Still old", "visibility": "shared"}]:
            response = client.patch(route, headers=alice, json=patch)
            assert response.status_code == 200, response.text
            assert client.get(route, headers=carol).status_code == 404
    assert client.get(A + "/memories?scope=shared", headers=carol).json()["total"] == 0
    assert client.get(A + "/trips?scope=shared", headers=carol).json()["total"] == 0
    assert client.get(A + "/map/footprints?scope=shared", headers=carol).json()["stats"]["visits"] == 0
    # Re-sharing is possible only through an explicit private -> shared transition.
    route = A + f"/memories/{old['id']}"
    assert client.patch(route, headers=alice, json={"visibility": "private"}).status_code == 200
    assert client.patch(route, headers=alice, json={"visibility": "shared"}).status_code == 200
    newly_shared = client.get(route, headers=carol)
    assert newly_shared.status_code == 200
    assert client.get(newly_shared.json()["photos"][0]["url"]).status_code == 200
    trip_route = A + f"/trips/{empty_trip['id']}"
    assert client.patch(trip_route, headers=alice, json={"visibility": "private"}).status_code == 200
    assert client.patch(trip_route, headers=alice, json={"visibility": "shared"}).status_code == 200
    assert client.get(trip_route, headers=carol).status_code == 200


def test_authors_can_edit_archived_shared_records_without_new_relationship(client):
    alice, bob = pair(client)
    old = memory(client, alice, visibility="shared").json()
    trip = client.post(A + "/trips", headers=alice, json={"title": "Old trip", "visibility": "shared"}).json()
    client.post(A + "/spaces/unbind", headers=alice)
    for resource, id in [("memories", old["id"]), ("trips", trip["id"])]:
        for patch in [{"title": "Author correction"}, {"title": "No new audience", "visibility": "shared"}]:
            response = client.patch(A + f"/{resource}/{id}", headers=alice, json=patch)
            assert response.status_code == 200, response.text
            assert client.get(A + f"/{resource}/{id}", headers=bob).status_code == 404

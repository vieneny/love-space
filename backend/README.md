# Love Space Python API

Python 3.12, FastAPI, synchronous SQLAlchemy, Alembic. SQLite is a local development option; production requires PostgreSQL (deployment target: PostgreSQL 17). No real users, trips, memories, or photos are seeded. Three starter daily questions are content templates, editable by an administrator.

## Local run

Run from `backend/`:

```powershell
uv sync --python 3.12
Copy-Item .env.example .env
# Edit .env: set an administrator password if the management app is needed.
uv run alembic upgrade head
uv run uvicorn app.main:app --host 127.0.0.1 --port 18100 --reload --no-access-log
```

API docs: `http://127.0.0.1:18100/docs`; live schema: `/openapi.json`; process health: `/health`.
`/ready` returns 200 only when a database query succeeds and the private media directory is readable/writable; failures return a generic 503 without connection details. The Docker health check uses `/ready`, and Compose waits for API health before starting the web proxy. This does not replace a storage-capacity check or a restore rehearsal.
Generate the checked-in schema with `uv run python -m app.export_openapi`.
App routes are under `/api/v1/app`; admin routes under `/api/v1/admin`. JSON is returned directly; lists use `{ "items": [], "total": 0 }`. JSON dates are `YYYY-MM-DD`.

For WeChat `wx.request`, send edits as `POST` with the exact header `X-HTTP-Method-Override: PATCH`. The server only converts POST requests below `/api/v1/app/`; admin routes, other methods, other override values, and duplicate override headers are not converted. The ordinary PATCH routes remain available for H5. Both forms run identical authentication and author/space permission checks.

`.env` is loaded relative to the working directory. No default admin password exists: an empty `ADMIN_PASSWORD` disables administrator login with HTTP 503. An omitted development `JWT_SECRET` creates a process-local secret, so tokens expire after a restart; set a local secret for durable sessions or multiple workers. Never reuse development identities in production.

For production set `ENVIRONMENT=production`, `DEV_LOGIN_ENABLED=false`, `DATABASE_URL=postgresql+psycopg://...`, `JWT_SECRET` (at least 32 bytes), and `ADMIN_PASSWORD` (at least 12 characters). Missing/unsafe production configuration prevents startup. Run migrations before starting. Configure actual WeChat AppID/secret; without them real WeChat login returns 503 and never falls back to development. The real server exchange calls WeChat `jscode2session`; production account login still needs validation using an authorized real AppID/code.

`PUBLIC_BASE_URL` defaults to `http://127.0.0.1:18100`. Media response URLs are relative and clients prefix their configured API origin. Configure exact `CORS_ORIGINS` for Web clients. The production reverse proxy must expose HTTPS; the application container is HTTP behind it. Keep port 18100 private behind that proxy. Do not log media query strings: signed URLs are temporary bearer capabilities.

The supplied Caddy proxy limits multipart media requests to 12 MB and other API request bodies to 256 KB; the application independently enforces its 10 MiB image limit. Container logs rotate at 10 MB with three files per service. The backend Docker build excludes environment files, databases, private media, and the local virtual environment from its build context.

## Restricted temporary preview gateway

For an explicitly configured temporary preview tunnel, forward the tunnel to `127.0.0.1:18102`, where `app.preview_gateway:app` runs separately from the existing API. Follow `docs/PUBLIC_PREVIEW.md` at the repository root for the preview launcher. The gateway does not import the backend application, read `.env`, restart it, or enable development login.

Set `PREVIEW_API_UPSTREAM` explicitly to the running API's private IPv4 HTTP origin, then start `uv run uvicorn app.preview_gateway:app --host 127.0.0.1 --port 18102 --no-access-log`. There is no default upstream. Only canonical RFC1918 IPv4 origins are accepted; DNS names, public/loopback/link-local addresses, credentials, URL paths and query strings prevent startup.

The gateway allows `/health` (GET/HEAD) and `/api/v1/app/*`, while always rejecting development login, admin routes, docs/OpenAPI, escaped paths and path traversal. App authentication and signed media authorization still run in the existing API. It preserves authorization and the app PATCH override, removes hop-by-hop and untrusted forwarding headers, never follows redirects, ignores proxy environment variables, and uses bounded connection/I/O timeouts. POST multipart media bodies are capped at 12 MiB; every other request body is capped at 256 KiB, including chunked requests. Upstream errors return generic 502/504 responses. HTTP client verbose logs are suppressed; keep Uvicorn access logs off because signed media queries must not enter logs. This is a temporary development preview, not a production deployment or an official WeChat experience-version upload.

## Privacy and relationship lifecycle

- Private records are visible only to their author. Personal scope returns everything authored by that account, including retained records from archived spaces. Shared scope returns only shared content in the current active space.
- A space has at most two members. Invites are cryptographically random, stored hashed, expire in 30 minutes, and are consumed with database conditional updates in one transaction. Issuing a new code revokes prior codes. Joining an existing space and creating a space both conditionally claim the user's empty membership.
- Unbinding archives the entire space and clears both current memberships. Each author retains their own memories/trips/media. Ex-partner content and old shared utilities become inaccessible. New relationships receive a new space. No old shared content is automatically exposed to a new partner.
- Editing an archived shared memory or trip preserves its original sharing space, including an explicit unchanged `visibility:"shared"`. This works even without a current relationship. To share it into a new relationship, the author must deliberately change it to private, then to shared; attached-trip consistency rules still apply. Changing a title or date never changes the audience.
- Shared trips only accept shared memories in the same space; private trips only accept owner-private memories. Changing trip visibility requires detaching all memories first. Deleting a trip detaches memories without deleting either author's content.
- Photo uploads accept verified JPEG, PNG or WebP (10 MiB, 30 million pixels by default), verify/decode the real image, reject MIME mismatches, and store random filenames outside public directories. Only owner-uploaded photos can be attached. File URLs bind the image and viewer; every retrieval checks current record authorization, so changing visibility, deletion, or unbinding revokes the ex-partner's issued URL. The author can still access their own uploads. Signed URLs last 30 minutes and use `private, no-store`.
- Map and timeline share memories. Map results require a full coordinate pair. Distinct places use rounded coordinates plus the original CRS; repeated dated visits remain separate. Text-only locations remain in the timeline. Coordinates are never silently converted; preserve `wgs84`/`gcj02` and IANA timezone. Connecting records does not represent GPS tracks.
- Today's question response `id` is the current space/day instance ID; pass that value as `question_id` when answering. The partner answer is withheld until both current members have answered. Habits check in once per member/day via a unique constraint. Day defaults use Asia/Shanghai; historical memory dates remain date-only.

## Admin API fields

Admin JWTs have a separate audience, cannot call app APIs, and app JWTs cannot call admin APIs. Login returns `{access_token,token_type}`. The server hashes the environment-supplied password using Argon2. Metadata reads and question mutations are audited; audit rows contain IDs/actions, not private content.

| Endpoint | Returned item / object |
| --- | --- |
| GET `/overview` | `{users,spaces,memories,trips,media_count,storage_bytes,wishes,habits}`; counts include archived spaces |
| GET `/users` | `{id,nickname,space_id,created_at}` |
| GET `/spaces` | `{id,title,start_date,active,member_count,created_at}` |
| GET `/memories` | `{id,author_id,space_id,trip_id,kind,visibility,occurred_on,created_at,photo_count}`; no private title/text/location/photo URLs |
| GET `/feedback` | `{id,author_id,content,created_at}`; user deliberately submits feedback to administrators |
| GET `/audit-logs` | `{id,actor,action,target_id,created_at}`, latest 500 rows |
| GET/POST `/questions`, PATCH `/questions/{id}` | `{id,text,active}`; POST `{text,active?}`, PATCH `{text?,active?}` |
| GET `/settings` | `{environment,dev_login_enabled,wechat_login_configured,media_max_bytes,media_storage:"private",map_provider:"unconfigured"}`; no secrets |

Example metadata response:

```json
{"items":[{"id":"memory-uuid","author_id":"user-uuid","space_id":null,"trip_id":null,"kind":"daily","visibility":"private","occurred_on":"2026-10-18","created_at":"2026-10-18T06:00:00","photo_count":0}],"total":1}
```

All admin list pages currently return the complete authorized list except audit logs (latest 500); pagination and distributed edge rate limits should be added before a large public rollout. No payment, phone monitoring, background tracking, or public photo serving is implemented. Map lookup/rendering providers are configured separately by the deployment; saved coordinates work independently.

## Verification

```powershell
uv run pytest -q
uv run alembic check
```

The suite checks tenant isolation, private/shared scope, parent/media injection, revocation of already issued file URLs, concurrent invitations and checkins, expiry/rotation, question unlocking, admin audience/privacy, real-login fail-closed behavior, CRS/date statistics, and production configuration guards.

For the same suite against a disposable PostgreSQL 17 database, set `LOVE_SPACE_TEST_DATABASE_URL=postgresql+psycopg://.../love_space_backend_test` and rerun `uv run pytest -q`. The fixture DROPS/RECREATES this dedicated test schema for each test and refuses a PostgreSQL database with any other name. Never point this variable at business data. SQLite test databases and uploaded test images live in pytest temporary folders.

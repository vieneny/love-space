from contextlib import asynccontextmanager
from datetime import date, datetime, timedelta, timezone
from io import BytesIO
import hashlib
import secrets
import warnings
from zoneinfo import ZoneInfo

import httpx
import jwt
from fastapi import FastAPI, Depends, HTTPException, Request, UploadFile, File, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from PIL import Image, UnidentifiedImageError
from pwdlib import PasswordHash
from pydantic import ValidationError
from sqlalchemy import select, update, delete, func, or_, and_
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from .config import Settings, get_settings
from .database import make_engine, session_factory
from .middleware import AppPatchOverrideMiddleware
from .models import (Base, User, Space, Invitation, Trip, Memory, Media, Anniversary, Wish,
                     Question, DailyQuestion, Answer, Mood, Habit, Checkin, Feedback, Audit, now, uid)
from . import schemas as S


def today():
    return datetime.now(ZoneInfo("Asia/Shanghai")).date()


def fail(status, detail):
    raise HTTPException(status, detail)


def listing(items):
    return {"items": items, "total": len(items)}


def create_app(settings: Settings | None = None):
    cfg = settings or get_settings()
    engine = make_engine(cfg.database_url)
    sessions = session_factory(engine)
    password_hash = PasswordHash.recommended()
    admin_hash = password_hash.hash(cfg.admin_password) if cfg.admin_password else None

    @asynccontextmanager
    async def lifespan(app):
        cfg.media_root.mkdir(parents=True, exist_ok=True)
        if cfg.environment != "production":
            Base.metadata.create_all(engine)
        with sessions.begin() as db:
            if not db.scalar(select(func.count()).select_from(Question)):
                for text in ["今天有什么小事让你开心？", "下次见面想一起做什么？", "最近希望我怎样陪伴你？"]:
                    db.add(Question(text=text))
        yield
        engine.dispose()

    app = FastAPI(title="Love Space API", version="0.1.0", lifespan=lifespan,
                  description="Private couple memories. All sharing follows current active space membership.")
    app.state.settings = cfg
    app.state.engine = engine
    app.state.sessions = sessions
    app.add_middleware(AppPatchOverrideMiddleware)
    app.add_middleware(CORSMiddleware, allow_origins=cfg.cors_origins.split(","),
                       allow_credentials=False, allow_methods=["GET", "POST", "PATCH", "DELETE"],
                       allow_headers=["Authorization", "Content-Type", "X-HTTP-Method-Override"])
    bearer = HTTPBearer(auto_error=False)
    A = "/api/v1/app"
    B = "/api/v1/admin"

    def db_session():
        with sessions() as db:
            try:
                yield db
                db.commit()
            except Exception:
                db.rollback()
                for filename in db.info.get("new_media_files", []):
                    (cfg.media_root / filename).unlink(missing_ok=True)
                raise

    def token(subject, audience="app", minutes=None, **extra):
        stamp = datetime.now(timezone.utc)
        return jwt.encode({"sub": subject, "aud": audience, "iat": stamp,
                           "exp": stamp + timedelta(minutes=minutes or cfg.access_token_minutes),
                           "jti": secrets.token_hex(16), **extra}, cfg.jwt_secret, algorithm="HS256")

    def decode(value, audience):
        try:
            return jwt.decode(value, cfg.jwt_secret, algorithms=["HS256"], audience=audience,
                              options={"require": ["sub", "exp", "iat", "aud"]})
        except jwt.PyJWTError:
            fail(401, "Invalid or expired token")

    def current_user(credentials: HTTPAuthorizationCredentials | None = Depends(bearer),
                     db: Session = Depends(db_session)):
        if not credentials:
            fail(401, "Authentication required")
        claims = decode(credentials.credentials, "app")
        user = db.get(User, claims["sub"])
        if not user:
            fail(401, "Account unavailable")
        return user

    def current_admin(credentials: HTTPAuthorizationCredentials | None = Depends(bearer)):
        if not credentials:
            fail(401, "Administrator authentication required")
        claims = decode(credentials.credentials, "admin")
        if claims["sub"] != cfg.admin_username or not admin_hash:
            fail(401, "Administrator unavailable")
        return claims["sub"]

    def user_out(u):
        return {"id": u.id, "nickname": u.nickname, "space_id": u.space_id}

    def active_space(db, user):
        space = db.get(Space, user.space_id) if user.space_id else None
        if not space or not space.active:
            fail(409, "An active couple space is required")
        return space

    def space_out(db, space):
        return {"id": space.id, "title": space.title, "start_date": space.start_date,
                "members": [user_out(u) for u in db.scalars(select(User).where(User.space_id == space.id))]}

    def audit(db, actor, action, target=None):
        db.add(Audit(actor=actor, action=action, target_id=target))

    def can_read(obj, user):
        return obj.author_id == user.id or (
            obj.visibility == "shared" and user.space_id is not None and obj.space_id == user.space_id
        )

    def readable(db, model, id, user):
        obj = db.get(model, id)
        if not obj or not can_read(obj, user):
            fail(404, "Record not found")
        return obj

    def owned(db, model, id, user):
        obj = readable(db, model, id, user)
        if obj.author_id != user.id:
            fail(403, "Only the author can change this record")
        return obj

    def scope_clause(model, scope, user):
        if scope == "personal":
            return model.author_id == user.id
        return and_(model.visibility == "shared", model.space_id == user.space_id) if user.space_id else model.id == ""

    def validate_payload(model, values):
        try:
            return model.model_validate(values)
        except ValidationError as exc:
            fail(422, str(exc))

    def assign(obj, values):
        for key, value in values.items():
            setattr(obj, key, value)

    def sharing_space(db, user, visibility, existing=None):
        if visibility == "private":
            return None
        # An ordinary edit never changes the audience of previously shared content.
        # Re-sharing archived content requires a deliberate private -> shared change.
        if existing is not None and existing.visibility == "shared":
            return existing.space_id
        return active_space(db, user).id

    def validate_memory(db, body, user, existing=None):
        space_id = sharing_space(db, user, body.visibility, existing)
        if body.trip_id:
            unchanged_parent = (existing is not None and existing.trip_id == body.trip_id
                                and existing.visibility == body.visibility and existing.space_id == space_id)
            # Authors can correct a retained memory whose unchanged parent belonged
            # to their former partner. This does not grant access to that parent's data.
            trip = db.get(Trip, body.trip_id) if unchanged_parent else readable(db, Trip, body.trip_id, user)
            if not trip:
                fail(404, "Trip not found")
            if trip.visibility != body.visibility:
                fail(422, "Trip and memory visibility must match")
            if body.visibility == "shared" and trip.space_id != space_id:
                fail(404, "Trip not in the current space")
            if body.visibility == "private" and trip.author_id != user.id:
                fail(404, "Trip not found")
        for photo_id in body.photo_ids:
            photo = db.get(Media, photo_id)
            if not photo or photo.owner_id != user.id:
                fail(404, "Photo not owned by this account")
        return space_id

    def media_url(photo_id, user):
        signed = token(user.id, "media", cfg.media_token_minutes, media_id=photo_id)
        return f"{A}/media/{photo_id}?token={signed}"

    def memory_out(db, m, user):
        author = db.get(User, m.author_id)
        return {"id": m.id, "title": m.title, "content": m.content, "occurred_on": m.occurred_on,
                "kind": m.kind, "visibility": m.visibility, "trip_id": m.trip_id, "place": m.place,
                "photos": [{"id": p, "url": media_url(p, user)} for p in m.photo_ids],
                "author_id": m.author_id, "author_name": author.nickname, "created_at": m.created_at}

    def trip_out(db, t, user):
        count = sum(1 for m in db.scalars(select(Memory).where(Memory.trip_id == t.id)) if can_read(m, user))
        return {"id": t.id, "title": t.title, "description": t.description,
                "start_date": t.start_date, "end_date": t.end_date, "visibility": t.visibility,
                "author_id": t.author_id, "memory_count": count}

    def memory_query(db, user, scope, trip_id=None, year=None, kind=None, country=None):
        query = select(Memory).where(scope_clause(Memory, scope, user)).order_by(Memory.occurred_on.desc(), Memory.id)
        if trip_id:
            readable(db, Trip, trip_id, user)
            query = query.where(Memory.trip_id == trip_id)
        if year:
            query = query.where(Memory.occurred_on >= date(year, 1, 1), Memory.occurred_on <= date(year, 12, 31))
        if kind:
            query = query.where(Memory.kind == kind)
        values = list(db.scalars(query))
        if country:
            values = [m for m in values if (m.place or {}).get("country_code", "").upper() == country.upper()]
        return values

    @app.get("/health")
    def health():
        return {"status": "ok"}

    def login_account(db, identity, nickname):
        user = db.scalar(select(User).where(User.identity == identity))
        if not user:
            try:
                with db.begin_nested():
                    user = User(identity=identity, nickname=nickname)
                    db.add(user)
                    db.flush()
            except IntegrityError:
                user = db.scalar(select(User).where(User.identity == identity))
        return {"access_token": token(user.id), "token_type": "bearer", "user": user_out(user)}

    @app.post(A + "/auth/dev-login", response_model=S.LoginOut, tags=["App authentication"])
    def dev_login(body: S.DevLogin, db: Session = Depends(db_session)):
        if cfg.environment not in {"development", "test"} or not cfg.dev_login_enabled:
            fail(404, "Development login disabled")
        return login_account(db, "dev:" + body.identity, body.nickname or body.identity)

    @app.post(A + "/auth/wechat-login", response_model=S.LoginOut, tags=["App authentication"])
    def wechat_login(body: S.WechatLogin, db: Session = Depends(db_session)):
        if not cfg.wechat_appid or not cfg.wechat_secret:
            fail(503, "WeChat login is not configured")
        try:
            with httpx.Client(timeout=10) as client:
                response = client.get("https://api.weixin.qq.com/sns/jscode2session", params={
                    "appid": cfg.wechat_appid, "secret": cfg.wechat_secret,
                    "js_code": body.code, "grant_type": "authorization_code"})
                response.raise_for_status()
                data = response.json()
        except (httpx.HTTPError, ValueError):
            fail(502, "WeChat authentication service unavailable")
        if data.get("errcode") or not data.get("openid"):
            fail(401, "WeChat code invalid or expired")
        return login_account(db, "wx:" + data["openid"], "微信用户")

    @app.get(A + "/me", response_model=S.UserOut)
    def me(user: User = Depends(current_user)):
        return user_out(user)

    @app.get(A + "/spaces/current", response_model=S.SpaceOut | None)
    def get_space(db: Session = Depends(db_session), user: User = Depends(current_user)):
        if not user.space_id:
            return None
        return space_out(db, active_space(db, user))

    @app.post(A + "/spaces", response_model=S.SpaceOut)
    def create_space(body: S.SpaceWrite, db: Session = Depends(db_session), user: User = Depends(current_user)):
        space = Space(**body.model_dump())
        db.add(space)
        db.flush()
        changed = db.execute(update(User).where(User.id == user.id, User.space_id.is_(None)).values(space_id=space.id))
        if changed.rowcount != 1:
            fail(409, "Already in a space")
        db.refresh(user)
        audit(db, user.id, "space.create", space.id)
        return space_out(db, space)

    @app.patch(A + "/spaces/current", response_model=S.SpaceOut)
    def patch_space(body: S.SpacePatch, db: Session = Depends(db_session), user: User = Depends(current_user)):
        space = active_space(db, user)
        data = {"title": space.title, "start_date": space.start_date, **body.model_dump(exclude_unset=True)}
        assign(space, validate_payload(S.SpaceWrite, data).model_dump())
        db.flush()
        return space_out(db, space)

    @app.post(A + "/spaces/invitations")
    def invite(db: Session = Depends(db_session), user: User = Depends(current_user)):
        space = active_space(db, user)
        if space.member_count >= 2:
            fail(409, "Space is full")
        db.execute(update(Invitation).where(Invitation.space_id == space.id, Invitation.used.is_(False)).values(used=True))
        code = secrets.token_urlsafe(12)
        expires = now() + timedelta(minutes=cfg.invite_minutes)
        db.add(Invitation(code_hash=hashlib.sha256(code.encode()).hexdigest(), space_id=space.id, expires_at=expires))
        return {"code": code, "expires_at": expires.replace(tzinfo=timezone.utc)}

    @app.post(A + "/spaces/join", response_model=S.SpaceOut)
    def join(body: S.Join, db: Session = Depends(db_session), user: User = Depends(current_user)):
        if user.space_id:
            fail(409, "Already in a space")
        digest = hashlib.sha256(body.code.encode()).hexdigest()
        space_id = db.execute(update(Invitation).where(
            Invitation.code_hash == digest, Invitation.used.is_(False), Invitation.expires_at > now()
        ).values(used=True).returning(Invitation.space_id)).scalar_one_or_none()
        if not space_id:
            fail(409, "Invitation expired or already used")
        changed = db.execute(update(Space).where(Space.id == space_id, Space.active.is_(True), Space.member_count < 2)
                             .values(member_count=Space.member_count + 1))
        if changed.rowcount != 1:
            fail(409, "Space is full or archived")
        changed = db.execute(update(User).where(User.id == user.id, User.space_id.is_(None)).values(space_id=space_id))
        if changed.rowcount != 1:
            fail(409, "Already in a space")
        db.refresh(user)
        audit(db, user.id, "space.join", space_id)
        return space_out(db, db.get(Space, space_id))

    @app.post(A + "/spaces/unbind")
    def unbind(db: Session = Depends(db_session), user: User = Depends(current_user)):
        space = active_space(db, user)
        db.execute(update(Space).where(Space.id == space.id).values(active=False, member_count=0))
        db.execute(update(User).where(User.space_id == space.id).values(space_id=None))
        db.execute(update(Invitation).where(Invitation.space_id == space.id).values(used=True))
        audit(db, user.id, "space.unbind", space.id)
        return {"ok": True}

    @app.get(A + "/memories", response_model=S.MemoryList)
    def memories(scope: S.Scope = "personal", trip_id: str | None = None,
                 year: int | None = Query(default=None, ge=1, le=9999), kind: S.Kind | None = None,
                 country: str | None = None, db: Session = Depends(db_session), user: User = Depends(current_user)):
        rows = memory_query(db, user, scope, trip_id, year, kind, country)
        return listing([memory_out(db, m, user) for m in rows])

    @app.post(A + "/memories", response_model=S.MemoryOut)
    def add_memory(body: S.MemoryWrite, db: Session = Depends(db_session), user: User = Depends(current_user)):
        space_id = validate_memory(db, body, user)
        m = Memory(**body.model_dump(), author_id=user.id, space_id=space_id)
        m.photo_ids = list(dict.fromkeys(m.photo_ids))
        db.add(m)
        db.flush()
        return memory_out(db, m, user)

    @app.get(A + "/memories/{id}", response_model=S.MemoryOut)
    def get_memory(id: str, db: Session = Depends(db_session), user: User = Depends(current_user)):
        return memory_out(db, readable(db, Memory, id, user), user)

    @app.patch(A + "/memories/{id}", response_model=S.MemoryOut)
    def patch_memory(id: str, body: S.MemoryPatch, db: Session = Depends(db_session), user: User = Depends(current_user)):
        m = owned(db, Memory, id, user)
        values = {key: getattr(m, key) for key in S.MemoryWrite.model_fields}
        values.update(body.model_dump(exclude_unset=True))
        validated = validate_payload(S.MemoryWrite, values)
        space_id = validate_memory(db, validated, user, existing=m)
        assign(m, validated.model_dump())
        m.space_id = space_id
        db.flush()
        return memory_out(db, m, user)

    @app.delete(A + "/memories/{id}")
    def delete_memory(id: str, db: Session = Depends(db_session), user: User = Depends(current_user)):
        db.delete(owned(db, Memory, id, user))
        return {"ok": True}

    @app.get(A + "/trips", response_model=S.TripList)
    def trips(scope: S.Scope = "personal", db: Session = Depends(db_session), user: User = Depends(current_user)):
        return listing([trip_out(db, t, user) for t in db.scalars(select(Trip).where(scope_clause(Trip, scope, user)))])

    @app.post(A + "/trips", response_model=S.TripOut)
    def add_trip(body: S.TripWrite, db: Session = Depends(db_session), user: User = Depends(current_user)):
        sid = active_space(db, user).id if body.visibility == "shared" else None
        t = Trip(**body.model_dump(), author_id=user.id, space_id=sid)
        db.add(t)
        db.flush()
        return trip_out(db, t, user)

    @app.get(A + "/trips/{id}", response_model=S.TripOut)
    def get_trip(id: str, db: Session = Depends(db_session), user: User = Depends(current_user)):
        return trip_out(db, readable(db, Trip, id, user), user)

    @app.patch(A + "/trips/{id}", response_model=S.TripOut)
    def patch_trip(id: str, body: S.TripPatch, db: Session = Depends(db_session), user: User = Depends(current_user)):
        t = owned(db, Trip, id, user)
        values = {key: getattr(t, key) for key in S.TripWrite.model_fields}
        values.update(body.model_dump(exclude_unset=True))
        validated = validate_payload(S.TripWrite, values)
        sid = sharing_space(db, user, validated.visibility, existing=t)
        if (t.visibility != validated.visibility or t.space_id != sid) and db.scalar(select(Memory.id).where(Memory.trip_id == t.id).limit(1)):
            fail(409, "Detach existing memories before changing trip visibility or space")
        assign(t, validated.model_dump())
        t.space_id = sid
        db.flush()
        return trip_out(db, t, user)

    @app.delete(A + "/trips/{id}")
    def delete_trip(id: str, db: Session = Depends(db_session), user: User = Depends(current_user)):
        t = owned(db, Trip, id, user)
        db.execute(update(Memory).where(Memory.trip_id == id).values(trip_id=None))
        db.delete(t)
        return {"ok": True}

    @app.get(A + "/map/footprints")
    def footprints(scope: S.Scope = "personal", trip_id: str | None = None,
                   year: int | None = Query(default=None, ge=1, le=9999),
                   db: Session = Depends(db_session), user: User = Depends(current_user)):
        rows = memory_query(db, user, scope, trip_id, year)
        mapped = [m for m in rows if m.place and m.place.get("latitude") is not None and m.place.get("longitude") is not None]
        countries, cities, places = set(), set(), set()
        for m in mapped:
            p = m.place
            country = p.get("country_code") or p.get("country_name") or ""
            if country:
                countries.add(country)
            if p.get("city"):
                cities.add((country, p["city"]))
            places.add((p.get("coordinate_system"), round(p["latitude"], 5), round(p["longitude"], 5)))
        return {"items": [memory_out(db, m, user) for m in mapped],
                "stats": {"countries": len(countries), "cities": len(cities), "places": len(places), "visits": len(mapped)}}

    @app.post(A + "/media", response_model=S.PhotoOut)
    def upload(file: UploadFile = File(...), db: Session = Depends(db_session), user: User = Depends(current_user)):
        allowed = {"JPEG": ("image/jpeg", ".jpg"), "PNG": ("image/png", ".png"), "WEBP": ("image/webp", ".webp")}
        raw = file.file.read(cfg.media_max_bytes + 1)
        if len(raw) > cfg.media_max_bytes:
            fail(413, "Image exceeds upload limit")
        try:
            with warnings.catch_warnings():
                warnings.simplefilter("error", Image.DecompressionBombWarning)
                with Image.open(BytesIO(raw)) as img:
                    fmt = img.format
                    if fmt not in allowed or img.width * img.height > 30_000_000:
                        fail(415, "Unsupported image format or dimensions")
                    img.verify()
                with Image.open(BytesIO(raw)) as img:
                    img.load()
        except (UnidentifiedImageError, OSError, ValueError, Image.DecompressionBombError, Image.DecompressionBombWarning):
            fail(415, "File is not a valid supported image")
        mime, suffix = allowed[fmt]
        if file.content_type != mime:
            fail(415, "Image MIME type does not match its contents")
        filename = secrets.token_hex(24) + suffix
        cfg.media_root.mkdir(parents=True, exist_ok=True)
        (cfg.media_root / filename).write_bytes(raw)
        db.info.setdefault("new_media_files", []).append(filename)
        media = Media(owner_id=user.id, filename=filename, mime=mime, size=len(raw))
        db.add(media)
        db.flush()
        return {"id": media.id, "url": media_url(media.id, user)}

    @app.get(A + "/media/{id}", include_in_schema=True)
    def download(id: str, token: str, db: Session = Depends(db_session)):
        claims = decode(token, "media")
        if claims.get("media_id") != id:
            fail(404, "Image not found")
        user = db.get(User, claims["sub"])
        media = db.get(Media, id)
        if not user or not media:
            fail(404, "Image not found")
        allowed = media.owner_id == user.id
        if not allowed and user.space_id:
            candidates = db.scalars(select(Memory).where(Memory.space_id == user.space_id, Memory.visibility == "shared"))
            allowed = any(id in m.photo_ids for m in candidates)
        if not allowed:
            fail(404, "Image not found")
        path = cfg.media_root / media.filename
        if not path.is_file():
            fail(404, "Image unavailable")
        return FileResponse(path, media_type=media.mime, headers={"Cache-Control": "private, no-store", "X-Content-Type-Options": "nosniff"})

    def shared_record(db, model, id, user):
        sid = active_space(db, user).id
        obj = db.get(model, id)
        if not obj or obj.space_id != sid:
            fail(404, "Record not found")
        return obj

    def simple_out(obj, fields):
        return {field: getattr(obj, field) for field in fields}

    ann_fields = ["id", "title", "date", "repeat_yearly"]
    wish_fields = ["id", "title", "description", "completed"]

    @app.get(A + "/anniversaries")
    def anniversaries(db: Session = Depends(db_session), user: User = Depends(current_user)):
        sid = active_space(db, user).id
        return listing([simple_out(x, ann_fields) for x in db.scalars(select(Anniversary).where(Anniversary.space_id == sid).order_by(Anniversary.date))])

    @app.post(A + "/anniversaries")
    def add_anniversary(body: S.AnniversaryWrite, db: Session = Depends(db_session), user: User = Depends(current_user)):
        obj = Anniversary(**body.model_dump(), space_id=active_space(db, user).id, author_id=user.id)
        db.add(obj)
        db.flush()
        return simple_out(obj, ann_fields)

    @app.patch(A + "/anniversaries/{id}")
    def patch_anniversary(id: str, body: S.AnniversaryPatch, db: Session = Depends(db_session), user: User = Depends(current_user)):
        obj = shared_record(db, Anniversary, id, user)
        values = {key: getattr(obj, key) for key in S.AnniversaryWrite.model_fields}
        values.update(body.model_dump(exclude_unset=True))
        assign(obj, validate_payload(S.AnniversaryWrite, values).model_dump())
        return simple_out(obj, ann_fields)

    @app.delete(A + "/anniversaries/{id}")
    def del_anniversary(id: str, db: Session = Depends(db_session), user: User = Depends(current_user)):
        db.delete(shared_record(db, Anniversary, id, user))
        return {"ok": True}

    @app.get(A + "/wishes")
    def wishes(db: Session = Depends(db_session), user: User = Depends(current_user)):
        sid = active_space(db, user).id
        return listing([simple_out(x, wish_fields) for x in db.scalars(select(Wish).where(Wish.space_id == sid))])

    @app.post(A + "/wishes")
    def add_wish(body: S.WishWrite, db: Session = Depends(db_session), user: User = Depends(current_user)):
        obj = Wish(**body.model_dump(), space_id=active_space(db, user).id, author_id=user.id)
        db.add(obj)
        db.flush()
        return simple_out(obj, wish_fields)

    @app.patch(A + "/wishes/{id}")
    def patch_wish(id: str, body: S.WishPatch, db: Session = Depends(db_session), user: User = Depends(current_user)):
        obj = shared_record(db, Wish, id, user)
        values = {key: getattr(obj, key) for key in S.WishWrite.model_fields}
        values.update(body.model_dump(exclude_unset=True))
        assign(obj, validate_payload(S.WishWrite, values).model_dump())
        return simple_out(obj, wish_fields)

    @app.delete(A + "/wishes/{id}")
    def del_wish(id: str, db: Session = Depends(db_session), user: User = Depends(current_user)):
        db.delete(shared_record(db, Wish, id, user))
        return {"ok": True}

    def daily_question(db, user):
        sid = active_space(db, user).id
        row = db.scalar(select(DailyQuestion).where(DailyQuestion.space_id == sid, DailyQuestion.day == today()))
        if not row:
            questions = list(db.scalars(select(Question).where(Question.active.is_(True)).order_by(Question.id)))
            if not questions:
                fail(503, "No active questions; administrator can add a question")
            question = questions[today().toordinal() % len(questions)]
            try:
                with db.begin_nested():
                    row = DailyQuestion(space_id=sid, day=today(), question_id=question.id, question_text=question.text)
                    db.add(row)
                    db.flush()
            except IntegrityError:
                row = db.scalar(select(DailyQuestion).where(DailyQuestion.space_id == sid, DailyQuestion.day == today()))
        return row

    def daily_out(db, row, user):
        answers = {a.author_id: a.answer for a in db.scalars(select(Answer).where(Answer.daily_id == row.id))}
        members = list(db.scalars(select(User.id).where(User.space_id == row.space_id)))
        both = len(members) == 2 and all(member in answers for member in members)
        partner_answer = next((a for author, a in answers.items() if author != user.id), None) if both else None
        return {"id": row.id, "question": row.question_text, "my_answer": answers.get(user.id),
                "partner_answer": partner_answer, "both_answered": both}

    @app.get(A + "/interaction/today")
    def interaction(db: Session = Depends(db_session), user: User = Depends(current_user)):
        return daily_out(db, daily_question(db, user), user)

    @app.post(A + "/interaction/answers")
    def answer(body: S.AnswerWrite, db: Session = Depends(db_session), user: User = Depends(current_user)):
        row = daily_question(db, user)
        if row.id != body.question_id:
            fail(404, "Question not found in today's current space")
        existing = db.scalar(select(Answer).where(Answer.daily_id == row.id, Answer.author_id == user.id))
        if existing:
            existing.answer = body.answer
        else:
            try:
                with db.begin_nested():
                    db.add(Answer(daily_id=row.id, author_id=user.id, answer=body.answer))
                    db.flush()
            except IntegrityError:
                db.execute(update(Answer).where(Answer.daily_id == row.id, Answer.author_id == user.id).values(answer=body.answer))
        db.flush()
        return daily_out(db, row, user)

    def mood_out(db, m):
        return {"id": m.id, "day": m.day, "mood": m.mood, "note": m.note, "visibility": m.visibility,
                "author_id": m.author_id, "author_name": db.get(User, m.author_id).nickname}

    @app.get(A + "/moods")
    def moods(scope: S.Scope = "personal", db: Session = Depends(db_session), user: User = Depends(current_user)):
        return listing([mood_out(db, m) for m in db.scalars(select(Mood).where(scope_clause(Mood, scope, user)).order_by(Mood.day.desc()))])

    @app.post(A + "/moods")
    def add_mood(body: S.MoodWrite, db: Session = Depends(db_session), user: User = Depends(current_user)):
        sid = active_space(db, user).id if body.visibility == "shared" else None
        mood = Mood(**body.model_dump(), author_id=user.id, space_id=sid, day=today())
        db.add(mood)
        db.flush()
        return mood_out(db, mood)

    def habit_out(db, habit, user):
        rows = list(db.scalars(select(Checkin).where(Checkin.habit_id == habit.id).order_by(Checkin.day)))
        return {"id": habit.id, "title": habit.title,
                "checkins": [{"day": c.day, "author_id": c.author_id} for c in rows],
                "checked_today": any(c.day == today() and c.author_id == user.id for c in rows)}

    @app.get(A + "/habits")
    def habits(db: Session = Depends(db_session), user: User = Depends(current_user)):
        sid = active_space(db, user).id
        return listing([habit_out(db, h, user) for h in db.scalars(select(Habit).where(Habit.space_id == sid))])

    @app.post(A + "/habits")
    def add_habit(body: S.HabitWrite, db: Session = Depends(db_session), user: User = Depends(current_user)):
        habit = Habit(title=body.title, space_id=active_space(db, user).id)
        db.add(habit)
        db.flush()
        return habit_out(db, habit, user)

    @app.post(A + "/habits/{id}/checkins")
    def checkin(id: str, body: S.CheckinWrite, db: Session = Depends(db_session), user: User = Depends(current_user)):
        habit = shared_record(db, Habit, id, user)
        day = body.day or today()
        if day > today():
            fail(422, "Cannot check in a future date")
        try:
            with db.begin_nested():
                db.add(Checkin(habit_id=id, author_id=user.id, day=day))
                db.flush()
        except IntegrityError:
            pass
        return habit_out(db, habit, user)

    @app.post(A + "/feedback")
    def feedback(body: S.FeedbackWrite, db: Session = Depends(db_session), user: User = Depends(current_user)):
        db.add(Feedback(author_id=user.id, content=body.content))
        return {"ok": True}

    # Administrator identities use a separate token audience and never reuse an app account.
    @app.post(B + "/auth/login", tags=["Admin authentication"])
    def admin_login(body: S.AdminLogin, db: Session = Depends(db_session)):
        if not admin_hash:
            fail(503, "Administrator login is not configured")
        valid_password = password_hash.verify(body.password, admin_hash)
        if not secrets.compare_digest(body.username.encode(), cfg.admin_username.encode()) or not valid_password:
            fail(401, "Invalid administrator credentials")
        audit(db, body.username, "admin.login")
        return {"access_token": token(body.username, "admin", 120), "token_type": "bearer"}

    @app.get(B + "/overview")
    def overview(db: Session = Depends(db_session), admin: str = Depends(current_admin)):
        tables = {"users": User, "spaces": Space, "memories": Memory, "trips": Trip,
                  "media_count": Media, "wishes": Wish, "habits": Habit}
        result = {key: db.scalar(select(func.count()).select_from(model)) for key, model in tables.items()}
        result["storage_bytes"] = db.scalar(select(func.coalesce(func.sum(Media.size), 0)))
        audit(db, admin, "admin.overview")
        return result

    @app.get(B + "/users")
    def admin_users(db: Session = Depends(db_session), admin: str = Depends(current_admin)):
        audit(db, admin, "admin.users")
        return listing([simple_out(u, ["id", "nickname", "space_id", "created_at"]) for u in db.scalars(select(User).order_by(User.created_at.desc()))])

    @app.get(B + "/spaces")
    def admin_spaces(db: Session = Depends(db_session), admin: str = Depends(current_admin)):
        audit(db, admin, "admin.spaces")
        return listing([simple_out(s, ["id", "title", "start_date", "active", "member_count", "created_at"]) for s in db.scalars(select(Space).order_by(Space.created_at.desc()))])

    @app.get(B + "/memories")
    def admin_memories(db: Session = Depends(db_session), admin: str = Depends(current_admin)):
        audit(db, admin, "admin.memories")
        fields = ["id", "author_id", "space_id", "trip_id", "kind", "visibility", "occurred_on", "created_at"]
        return listing([{**simple_out(m, fields), "photo_count": len(m.photo_ids)} for m in db.scalars(select(Memory).order_by(Memory.created_at.desc()))])

    @app.get(B + "/feedback")
    def admin_feedback(db: Session = Depends(db_session), admin: str = Depends(current_admin)):
        audit(db, admin, "admin.feedback")
        return listing([simple_out(f, ["id", "author_id", "content", "created_at"]) for f in db.scalars(select(Feedback).order_by(Feedback.created_at.desc()))])

    @app.get(B + "/audit-logs")
    def audit_logs(db: Session = Depends(db_session), admin: str = Depends(current_admin)):
        return listing([simple_out(a, ["id", "actor", "action", "target_id", "created_at"]) for a in db.scalars(select(Audit).order_by(Audit.created_at.desc()).limit(500))])

    @app.get(B + "/questions")
    def questions(db: Session = Depends(db_session), admin: str = Depends(current_admin)):
        return listing([simple_out(q, ["id", "text", "active"]) for q in db.scalars(select(Question).order_by(Question.id))])

    @app.post(B + "/questions")
    def add_question(body: S.QuestionWrite, db: Session = Depends(db_session), admin: str = Depends(current_admin)):
        q = Question(**body.model_dump())
        db.add(q)
        db.flush()
        audit(db, admin, "question.create", q.id)
        return simple_out(q, ["id", "text", "active"])

    @app.patch(B + "/questions/{id}")
    def patch_question(id: str, body: S.QuestionPatch, db: Session = Depends(db_session), admin: str = Depends(current_admin)):
        q = db.get(Question, id)
        if not q:
            fail(404, "Question not found")
        data = {"text": q.text, "active": q.active, **body.model_dump(exclude_unset=True)}
        assign(q, validate_payload(S.QuestionWrite, data).model_dump())
        audit(db, admin, "question.update", q.id)
        return simple_out(q, ["id", "text", "active"])

    @app.get(B + "/settings")
    def settings_out(admin: str = Depends(current_admin)):
        return {"environment": cfg.environment, "dev_login_enabled": cfg.dev_login_enabled and cfg.environment != "production",
                "wechat_login_configured": bool(cfg.wechat_appid and cfg.wechat_secret),
                "media_max_bytes": cfg.media_max_bytes, "media_storage": "private", "map_provider": "unconfigured"}

    return app


app = create_app()

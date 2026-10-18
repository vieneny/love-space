# API contract — v1

Base `/api/v1/app`, JSON responses directly (no data envelope). IDs strings. Lists `{items:[],total:number}`. Dates `YYYY-MM-DD`. Auth `Authorization: Bearer <access_token>`. Errors FastAPI `{detail:string}`. All app routes below relative to base.

WeChat transport: a `POST` request below `/api/v1/app/` with exactly one `X-HTTP-Method-Override: PATCH` header is routed as PATCH. Other methods, targets, duplicate headers or values do not activate this compatibility mode. Normal authentication and permission checks remain required. H5 continues to use ordinary PATCH.

## Accounts / space
- `POST /auth/dev-login` `{identity,nickname?}` -> `{access_token,token_type,user}`. Development ONLY; disabled in production. No seeded real users.
- `POST /auth/wechat-login` `{code}` -> same; real server-side code exchange; missing credentials is explicit 503, never fallback login.
- `GET /me` -> `{id,nickname,space_id:null|string}`.
- `GET /spaces/current` -> null or `{id,title,start_date,members:[{id,nickname}]}`.
- `POST /spaces` `{title,start_date?}` -> space; one active space/user, max 2 members.
- `PATCH /spaces/current` `{title?,start_date?}`.
- `POST /spaces/invitations` -> `{code,expires_at}`; expiring/single-use, atomic joining.
- `POST /spaces/join` `{code}` -> space.
- `POST /spaces/unbind` -> `{ok:true}`; archive entire space/revoke both memberships. Own authored content remains accessible, partner's content revoked. New relationship gets new space.

## Memories, trips, map
- `GET /memories?scope=personal|shared&trip_id=&year=&kind=&country=` -> list. personal = authored by current user; shared = shared in CURRENT active space. Optional filters combined.
- `GET /memories/{id}`, `POST /memories`, `PATCH /memories/{id}`, `DELETE /memories/{id}`. Only author edits/deletes.
- Memory `{id,title,content,occurred_on,kind,visibility,trip_id,place,photos:[],author_id,author_name,created_at}`.
- Write `{title,content,occurred_on,kind:'travel'|'milestone'|'daily',visibility:'private'|'shared',trip_id?:string|null,place?:Place|null,photo_ids?:string[]}`. Default private. Shared needs current space. A shared trip may only contain shared records from its own space. Private trips/records visible only to owner. Parent and media authorization checked, no cross-space IDs.
- Place `{name,country_code,country_name,city,latitude,longitude,coordinate_system:'wgs84'|'gcj02',timezone?:string}`. Coordinates optional as a pair for text-only location; country/city optional. Preserve CRS/source, no blind conversion. Date-only remains date-only.
- `GET /trips?scope=personal|shared` -> list; `POST /trips`, `GET/PATCH/DELETE /trips/{id}`.
- Trip `{id,title,description,start_date,end_date,visibility,author_id,memory_count}`. POST/PATCH fields title,description,start_date,end_date,visibility. Deleting detaches memories, not destroy others' content.
- `GET /map/footprints?scope=personal|shared&trip_id=&year=` -> `{items:Memory[],stats:{countries,cities,places,visits}}`; mapped items require coordinates; distinct places vs repeated visits. Same visibility as timeline; count only authorized records. Source-order lines are not GPS tracks.
- `POST /media` multipart `file` -> `{id,url}`. `photos` are `{id,url}`. File URLs must work in image tags and enforce authorization even after unbinding, no public static uploads. Restrict MIME/size, verify image, random filenames.

## Life / interaction
- `GET/POST /anniversaries`, `PATCH/DELETE /anniversaries/{id}`; `{id,title,date,repeat_yearly}` (shared current space).
- `GET/POST /wishes`, `PATCH/DELETE /wishes/{id}`; `{id,title,description,completed}` (shared current space).
- `GET /interaction/today` -> `{id,question,my_answer:null|string,partner_answer:null|string,both_answered:boolean}`. Partner answer only visible after both answered, active membership required.
- `POST /interaction/answers` `{question_id,answer}` -> above.
- `GET /moods?scope=personal|shared` -> list; `POST /moods` `{mood,note,visibility}` -> `{id,day,mood,note,visibility,author_id,author_name}`.
- `GET/POST /habits` -> list or habit `{id,title,checkins:[],checked_today:boolean}`; `POST /habits/{id}/checkins` `{day?:YYYY-MM-DD}` idempotent; shared current space.
- `POST /feedback` `{content}` -> `{ok:true}`.

## Admin
Base `/api/v1/admin`, separate admin identity/token audience. `POST /auth/login` `{username,password}` -> `{access_token,token_type}`.
- GET `/overview` -> `{users,spaces,memories,trips,media_count,storage_bytes,wishes,habits}`.
- GET `/users`, `/spaces`, `/memories`, `/feedback`, `/audit-logs` -> lists. Metadata only, no private titles/text/coordinates/photo URLs in admin memory list.
- GET/POST `/questions`, PATCH `/questions/{id}` -> `{id,text,active}`.
- GET `/settings` -> sanitized service capability/status, no secrets; PATCH nonsecret feature settings if implemented.

## Clients
API base default `http://127.0.0.1:18100`; configured through env. relative file URLs prefixed with base. Production release MUST require HTTPS API, real AppID and dev login disabled. Display no fake map photos or invented travel statistics in empty accounts. Demo data is explicit development-only, not proof of working cloud sync. All UI actions handle loading/failure and persist through API.

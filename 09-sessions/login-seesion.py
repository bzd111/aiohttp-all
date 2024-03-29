import asyncio
import io
import sqlite3
from pathlib import Path
from typing import Any, AsyncIterator, Awaitable, Callable, Dict

import aiohttp_jinja2
import aiohttp_session
import aiosqlite
import jinja2
import PIL
import PIL.Image
from aiohttp import web


router = web.RouteTableDef()
_WebHandler = Callable[[web.Request], Awaitable[web.StreamResponse]]


def require_login(func: _WebHandler) -> _WebHandler:
    func.__require_login__ = True
    return func


@web.middleware
async def error_middleware(
    request: web.Request, handler: _WebHandler
) -> web.StreamResponse:
    try:
        return await handler(request)
    except web.HTTPException:
        raise
    except asyncio.CancelledError:
        raise
    except Exception as ex:
        return aiohttp_jinja2.render_template(
            "error-page.html", request, {"error_text": str(ex)}, status=400
        )


@web.middleware
async def check_login(request: web.Request, handler: _WebHandler):
    require_login = getattr(handler, "__require_login__", False)
    session = await aiohttp_session.get_session(request)
    username = session.get("username")
    if require_login:
        if not username:
            raise web.HTTPSeeOther(location=f"/login")
    return await handler(request)


async def fetch_post(db: aiosqlite.Connection, post_id: int) -> Dict[str, Any]:
    async with db.execute(
        "select owner, editor, title, text, image from posts where id = ?", [post_id]
    ) as cursor:
        row = await cursor.fetchone()
        print(row)
        if row is None:
            raise RuntimeError(f"Post {post_id} does not exist")
        return {
            "id": post_id,
            "owner": row["owner"],
            "editor": row["editor"],
            "title": row["title"],
            "text": row["text"],
            "image": row["image"],
        }


async def apply_image(
    db: aiosqlite.Connection, post_id: int, img_context: bytes
) -> None:
    buf = io.BytesIO(img_context)
    loop = asyncio.get_event_loop()
    img = PIL.Image.open(buf)
    new_img = await loop.run_in_executor(None, img.resize, (64, 64), PIL.Image.LANCZOS)
    out_buf = io.BytesIO()
    new_img.save(out_buf, format="JPEG")
    await db.execute(
        "update posts set image = ? where id=?", [out_buf.getvalue(), post_id]
    )


@router.get("/login")
@aiohttp_jinja2.template("login.html")
async def login(request: web.Request) -> Dict[str, Any]:
    return {}


@router.post("/login")
async def login_apply(request: web.Request) -> web.Response:
    session = await aiohttp_session.get_session(request)
    form = await request.post()
    session["username"] = form["login"]
    raise web.HTTPSeeOther(location="/")


@router.get("/logout")
async def logout(request: web.Request) -> web.Response:
    session = await aiohttp_session.get_session(request)
    session["username"] = None
    raise web.HTTPSeeOther(location="/")


@router.get("/")
@aiohttp_jinja2.template("index.html")
async def index(request: web.Request) -> Dict[str, Any]:
    ret = []
    db = request.config_dict["DB"]
    async with db.execute("select id, owner, editor, title from posts") as cursor:
        async for row in cursor:
            ret.append(
                {
                    "id": row["id"],
                    "owner": row["owner"],  # this is have a KeyError
                    "editor": row["editor"],
                    "title": row["title"],
                }
            )
    return {"posts": ret}


@router.get("/new")
@require_login
@aiohttp_jinja2.template("new.html")
async def new_post(request: web.Request) -> Dict[str, Any]:
    return {}


@router.post("/new")
@require_login
@aiohttp_jinja2.template("edit.html")
async def new_post_apply(request: web.Request) -> Dict[str, Any]:
    db = request.config_dict["DB"]
    post = await request.post()
    session = await aiohttp_session.get_session(request)
    owner = session["username"]

    async with db.execute(
        "insert into posts (owner, editor, title, text) values (?,?,?,?)",
        [owner, owner, post["title"], post["text"]],
    ) as cursor:
        post_id = cursor.lastrowid
    image = post.get("image")
    if image:
        img_context = image.file.read()
        await apply_image(db, post_id, img_context)
    await db.commit()
    raise web.HTTPSeeOther(location=f"/")


@router.get("/{post}")
@aiohttp_jinja2.template("view.html")
async def view_post(request: web.Request) -> Dict[str, Any]:
    post_id = request.match_info["post"]
    if post_id.endswith(".ico"):
        raise web.HTTPSeeOther(location=f"/")
    db = request.config_dict["DB"]
    return {"post": await fetch_post(db, post_id)}


@router.get("/{post}/edit")
@require_login
@aiohttp_jinja2.template("edit.html")
async def edit_post(request: web.Request) -> Dict[str, Any]:
    post_id = request.match_info["post"]
    db = request.config_dict["DB"]
    return {"post": await fetch_post(db, post_id)}


@router.post("/{post}/edit")
@require_login
async def edit_post_apply(request: web.Request) -> web.Response:
    post_id = request.match_info["post"]
    db = request.config_dict["DB"]
    post = await request.post()
    image = post.get("image")
    await db.execute(
        "update posts set title=?, text=? where id =?",
        [post["title"], post["text"], post_id],
    )
    if image:
        img_content = image.file.read()
        await apply_image(db, post_id, img_content)
    await db.commit()
    raise web.HTTPSeeOther(location=f"/{post_id}")


@router.get("/{post}/delete")
async def delete_post(request: web.Request) -> web.Response:
    post_id = request.match_info["post"]
    db = request.config_dict["DB"]
    await db.execute("delete from posts where id=?", [post_id])
    raise web.HTTPSeeOther(location=f"/")


@router.get("/{post}/image")
async def render_post_image(request: web.Request) -> web.Response:
    post_id = request.match_info["post"]
    db = request.config_dict["DB"]
    async with db.execute("select image from posts where id = ?", [post_id]) as cursor:
        row = await cursor.fetchone()
        if row is None or row["image"] is None:
            img = PIL.Image.new("RGB", (64, 64), color=0)
            fp = io.BytesIO()
            img.save(fp, format="JPEG")
            content = fp.getvalue()
        else:
            content = row["image"]
    return web.Response(body=content, content_type="image/jpeg")


async def username_ctx_processor(request: web.Request) -> Dict[str, Any]:
    session = await aiohttp_session.get_session(request)
    username = session.get("username")
    return {"username": username}


def get_db_path() -> Path:
    here = Path.cwd()
    return here / "error.sqlite3"


async def init_db(app: web.Application) -> AsyncIterator[None]:
    sqlite_db = get_db_path()
    db = await aiosqlite.connect(sqlite_db)
    db.row_factory = aiosqlite.Row
    app["DB"] = db
    yield
    await db.close()


async def init_app() -> web.Application:
    app = web.Application()
    app.add_routes(router)
    app.cleanup_ctx.append(init_db)
    aiohttp_session.setup(app, aiohttp_session.SimpleCookieStorage())
    aiohttp_jinja2.setup(
        app,
        loader=jinja2.FileSystemLoader(str(Path.cwd() / "templates")),
        context_processors=[username_ctx_processor],
    )
    app.middlewares.append(error_middleware)
    app.middlewares.append(check_login)
    return app


def try_make_db() -> None:
    sqlite_db = get_db_path()
    if sqlite_db.exists():
        return

    with sqlite3.connect(sqlite_db) as conn:
        cur = conn.cursor()
        cur.execute(
            """CREATE TABLE posts (
            id INTEGER PRIMARY KEY,
            title TEXT,
            text TEXT,
            owner TEXT,
            editor TEXT,
            image BLOB)
        """
        )
        conn.commit()


try_make_db()


web.run_app(init_app())

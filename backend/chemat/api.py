import asyncio
from contextlib import asynccontextmanager
import os
import time
from collections import defaultdict, deque

from fastapi import FastAPI, Header, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from .engine import RuleError
from .store import Store


def create_app(store=None, clock=time.time, background=True):
    @asynccontextmanager
    async def lifespan(app):
        if app.state.store is None:
            app.state.store = Store(os.environ.get('CHEMAT_DATABASE_PATH', 'storage/chemat.sqlite3'),
                                    int(os.environ.get('CHEMAT_TURN_SECONDS', '60')),
                                    int(os.environ.get('CHEMAT_NEGOTIATION_SECONDS', '30')))
        async def timer():
            while True:
                await asyncio.sleep(1)
                app.state.store.tick_all(clock())
                for mid in list(sockets):
                    await broadcast(mid)
        task = asyncio.create_task(timer()) if background else None
        yield
        if task:
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass

    app = FastAPI(title='CHEMa’t amended engine', lifespan=lifespan)
    app.add_middleware(CORSMiddleware,allow_origins=os.environ.get('CHEMAT_ALLOWED_ORIGINS','http://localhost:8080,http://127.0.0.1:8080').split(','),allow_methods=['GET','POST','PATCH','DELETE'],allow_headers=['Content-Type','X-Player-ID','X-Device-Credential'])
    app.state.store = store
    sockets = {}
    socket_tokens = {}
    request_windows=defaultdict(deque)

    @app.middleware('http')
    async def request_limits(request,call_next):
        path=request.url.path
        try:
            content_length=int(request.headers.get('content-length','0') or 0)
        except ValueError:
            return JSONResponse(status_code=400,content={'error':'Invalid content length'})
        if content_length>65536:
            return JSONResponse(status_code=413,content={'error':'Request body too large'})
        if request.method=='POST' and path in ('/players','/sessions'):
            key=(request.client.host if request.client else 'unknown',path)
            window=request_windows[key]
            now=clock()
            while window and window[0]<=now-60:window.popleft()
            if len(window)>=(30 if path=='/players' else 120):
                return JSONResponse(status_code=429,content={'error':'Too many requests; retry later'})
            window.append(now)
        return await call_next(request)

    def db():
        return app.state.store

    def auth(pid, token):
        try:
            return db().authenticate(pid, token, clock())
        except RuleError as exc:
            raise HTTPException(401, 'Invalid credentials') from exc

    @app.exception_handler(RuleError)
    async def invalid(request, exc):
        return JSONResponse(status_code=409, content={'error': str(exc)})

    @app.get('/health')
    def health():
        return {'status': 'ok', 'milestone': 2, 'multiplayer_ready': False,
                'protocol_available': True, 'release_ready': False}

    @app.post('/players')
    def register(body: dict):
        return db().register(body.get('username'))

    @app.post('/sessions')
    def session(body:dict):
        try:
            return db().session(body.get('player_id'),body.get('credential'),clock())
        except RuleError as exc:
            raise HTTPException(401,'Invalid credentials') from exc

    @app.get('/players/me')
    def profile(x_player_id:str=Header(),x_device_credential:str=Header()):
        return db().profile(auth(x_player_id,x_device_credential))

    @app.get('/usernames/{username}')
    def available(username:str):
        return {'available':db().available(username)}

    @app.get('/players/search')
    def search(q:str,x_player_id:str=Header(),x_device_credential:str=Header()):
        auth(x_player_id,x_device_credential)
        return db().search(q)

    @app.get('/catalog')
    def get_catalog():
        from .engine import catalog
        from .card_help import ACTION_HELP
        data=catalog()
        for card in data['action']:
            card['description']=ACTION_HELP[card['name']]
            card['requires_target']=(card['category']=='attack' and card['name']!='Supply Shortage') or card['name'] in ('Market Swap','Unexpected Catalyst')
        return data

    @app.post('/players/me/revoke')
    def revoke(x_player_id:str=Header(),x_device_credential:str=Header()):
        db().revoke(auth(x_player_id,x_device_credential))
        return {'ok':True}

    @app.delete('/friends/{other}')
    def remove_friend(other:str,x_player_id:str=Header(),x_device_credential:str=Header()):
        db().remove_friend(auth(x_player_id,x_device_credential),other)
        return {'ok':True}

    @app.patch('/players/me')
    def rename(body: dict, x_player_id: str = Header(), x_device_credential: str = Header()):
        pid = auth(x_player_id,x_device_credential)
        db().rename(pid,body.get('username'))
        return {'ok': True}

    @app.get('/friends')
    def friends(x_player_id: str = Header(), x_device_credential: str = Header()):
        return db().friends(auth(x_player_id,x_device_credential))

    @app.post('/friends/request')
    def friend_request(body: dict, x_player_id: str = Header(), x_device_credential: str = Header()):
        db().friend_request(auth(x_player_id,x_device_credential),body.get('target',''))
        return {'ok': True}

    @app.post('/friends/accept')
    def friend_accept(body: dict, x_player_id: str = Header(), x_device_credential: str = Header()):
        db().friend_accept(auth(x_player_id,x_device_credential),body.get('sender',''))
        return {'ok': True}

    @app.post('/lobbies')
    def lobby(body: dict, x_player_id: str = Header(), x_device_credential: str = Header()):
        return {'code': db().lobby(auth(x_player_id,x_device_credential), bool(body.get('public',False)),clock())}

    @app.post('/matchmaking')
    def matchmaking(x_player_id: str = Header(), x_device_credential: str = Header()):
        return {'code': db().matchmaking(auth(x_player_id,x_device_credential),clock())}

    @app.get('/lobbies/{code}')
    def lobby_view(code: str, x_player_id: str = Header(), x_device_credential: str = Header()):
        return db().lobby_view(auth(x_player_id,x_device_credential),code,clock())

    @app.post('/lobbies/{code}/join')
    def join(code: str, x_player_id: str = Header(), x_device_credential: str = Header()):
        db().join(auth(x_player_id,x_device_credential),code,clock())
        return {'ok': True}

    @app.post('/lobbies/{code}/start')
    def start(code: str, x_player_id: str = Header(), x_device_credential: str = Header()):
        return {'match_id': db().start(auth(x_player_id,x_device_credential),code,clock(),require_ready=True)}

    @app.post('/lobbies/{code}/{operation}')
    def lobby_change(code:str,operation:str,x_player_id:str=Header(),x_device_credential:str=Header()):
        db().lobby_change(auth(x_player_id,x_device_credential),code,operation)
        return {'ok':True}

    @app.get('/matches/{mid}')
    def view(mid: str, x_player_id: str = Header(), x_device_credential: str = Header()):
        return db().view(auth(x_player_id,x_device_credential),mid)

    async def broadcast(mid):
        for ws,pid in list(sockets.get(mid, {}).items()):
            try:
                db().authenticate(pid,socket_tokens[ws],clock())
                await ws.send_json(db().view(pid,mid))
            except RuleError:
                sockets.get(mid,{}).pop(ws,None)
                try:
                    await ws.close(code=1008)
                except RuntimeError:
                    pass
            except (RuntimeError, WebSocketDisconnect):
                sockets.get(mid,{}).pop(ws,None)

    @app.post('/matches/{mid}/commands')
    async def command(mid: str, body: dict, x_player_id: str = Header(), x_device_credential: str = Header()):
        result = db().command(auth(x_player_id,x_device_credential),mid,body.get('request_id'),
                              body.get('version'),body.get('command'),body.get('args',{}),clock())
        await broadcast(mid)
        return result

    @app.get('/leaderboard')
    def leaderboard():
        return db().leaderboard(clock())

    @app.get('/leaderboard/friends')
    def friends_leaderboard(x_player_id:str=Header(),x_device_credential:str=Header()):
        return db().friends_leaderboard(auth(x_player_id,x_device_credential),clock())

    @app.websocket('/matches/{mid}/ws')
    async def websocket(ws: WebSocket, mid: str):
        await ws.accept()
        pid = None
        try:
            hello = await asyncio.wait_for(ws.receive_json(), timeout=10)
            pid = db().authenticate(hello.get('player_id'),hello.get('credential'),clock())
            db().view(pid,mid)
            db().connection(pid,mid,clock(),True)
            sockets.setdefault(mid,{})[ws] = pid
            socket_tokens[ws]=hello.get('credential')
            await ws.send_json(db().view(pid,mid))
            while True:
                body = await ws.receive_json()
                try:
                    db().authenticate(pid,hello.get('credential'),clock())
                    result = db().command(pid,mid,body.get('request_id'),body.get('version'),
                                          body.get('command'),body.get('args',{}),clock())
                    await ws.send_json({'receipt': result})
                    await broadcast(mid)
                except RuleError as exc:
                    await ws.send_json({'error': str(exc)})
        except (RuleError, ValueError, TypeError, AttributeError, asyncio.TimeoutError):
            await ws.close(code=1008)
        except WebSocketDisconnect:
            pass
        finally:
            sockets.get(mid,{}).pop(ws,None)
            socket_tokens.pop(ws,None)
            if pid and pid not in sockets.get(mid,{}).values():
                try:
                    db().connection(pid,mid,clock(),False)
                except RuleError:
                    pass

    return app


app = create_app()

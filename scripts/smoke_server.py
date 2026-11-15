"""Start a real uvicorn subprocess and exercise authenticated lobby/turn HTTP flow."""
import json
import os
from pathlib import Path
import socket
import subprocess
import sys
import tempfile
import time
from urllib.request import Request, urlopen

ROOT=Path(__file__).resolve().parents[1]


def main():
    with socket.socket() as probe:
        probe.bind(('127.0.0.1',0))
        port=probe.getsockname()[1]
    base=f'http://127.0.0.1:{port}'

    def call(path, body=None, account=None):
        headers={'Content-Type':'application/json'}
        if account:
            headers.update({'X-Player-ID':account['player_id'],'X-Device-Credential':account['credential']})
        req=Request(base+path,data=json.dumps(body).encode() if body is not None else None,headers=headers)
        with urlopen(req,timeout=5) as response:
            return json.load(response)

    with tempfile.TemporaryDirectory(prefix='chemat-smoke-') as folder:
        env={**os.environ,'PYTHONPATH':str(ROOT/'backend'),'CHEMAT_DATABASE_PATH':str(Path(folder)/'smoke.sqlite3')}
        with open(Path(folder)/'server.log','w+') as log:
            server=subprocess.Popen([sys.executable,'-m','uvicorn','chemat.api:app','--host','127.0.0.1','--port',str(port)],cwd=ROOT,env=env,stdout=log,stderr=log)
            try:
                for _ in range(100):
                    try:
                        assert call('/health')['status']=='ok'
                        break
                    except OSError:
                        if server.poll() is not None:
                            raise RuntimeError('Server exited during startup')
                        time.sleep(0.1)
                else:
                    raise TimeoutError('Server startup timeout')
                accounts=[call('/players',{'username':name}) for name in ('smoke-a','smoke-b')]
                code=call('/lobbies',{},accounts[0])['code']
                call(f'/lobbies/{code}/join',{},accounts[1])
                for account in accounts:
                    call(f'/lobbies/{code}/ready',{},account)
                mid=call(f'/lobbies/{code}/start',{},accounts[0])['match_id']
                state=call(f'/matches/{mid}',account=accounts[0])
                actor=next(a for a in accounts if a['player_id']==state['state']['current'])
                result=call(f'/matches/{mid}/commands',{'request_id':'smoke-end','version':0,'command':'end_turn'},actor)
                assert result['version']==1 and result['state']['current']!=actor['player_id']
                assert Path(env['CHEMAT_DATABASE_PATH']).is_file()
                print(json.dumps({'health':'ok','authenticated_lobby':'ok','authoritative_turn':'ok','sqlite':'ok'}))
            finally:
                server.terminate()
                server.wait(timeout=10)


if __name__=='__main__':
    main()

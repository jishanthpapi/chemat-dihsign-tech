"""Reproduce UI-only play against a real, restarted FastAPI server. No state injection."""
from pathlib import Path
from contextlib import closing
import json
import os
import shutil
import socket
import sqlite3
import subprocess
import sys
import tempfile
import time
from urllib.request import urlopen

ROOT=Path(__file__).resolve().parents[1]


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    flutter=shutil.which('flutter') or str(ROOT/'.tools/flutter/bin/flutter.bat')
    if not Path(flutter).is_file():
        raise SystemExit('Install Flutter and put it on PATH first')
    with socket.socket() as probe:
        probe.bind(('127.0.0.1',0));port=probe.getsockname()[1]
    base=f'http://127.0.0.1:{port}'
    reports=ROOT/'reports/two-client-ui';reports.mkdir(parents=True,exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='chemat-ui-server-') as folder:
        db=Path(folder)/'server.sqlite3';signal=Path(folder)/'restart'
        env={**os.environ,'PYTHONPATH':str(ROOT/'backend'),'CHEMAT_DATABASE_PATH':str(db),
             'CHEMAT_TURN_SECONDS':'3600','CHEMAT_NEGOTIATION_SECONDS':'180'}
        with open(reports/'server.log','w') as server_log,open(reports/'flutter.log','w') as flutter_log:
            def start():
                process=subprocess.Popen([sys.executable,'-m','uvicorn','chemat.api:app','--host','127.0.0.1','--port',str(port)],cwd=ROOT,env=env,stdout=server_log,stderr=server_log)
                for _ in range(100):
                    try:
                        with urlopen(base+'/health',timeout=1) as response:assert json.load(response)['status']=='ok'
                        return process
                    except OSError:time.sleep(.1)
                process.terminate();raise RuntimeError('Server failed to start')
            server=start()
            test=None
            server_exit_codes=[]
            try:
                test=subprocess.Popen([flutter,'test','--concurrency=1','test/two_client_live_test.dart','test/cleanup_live_probe_test.dart',f'--dart-define=LIVE_BACKEND={base}',
                                       f'--dart-define=RESTART_SIGNAL={signal.as_posix()}','--reporter','expanded'],cwd=ROOT/'mobile',stdout=flutter_log,stderr=flutter_log)
                restarted=False
                while test.poll() is None:
                    if signal.exists() and not restarted:
                        server.terminate();server_exit_codes.append(server.wait(timeout=10))
                        server=start();restarted=True
                        signal.with_suffix('.ack').write_text('restarted')
                        print('Backend restarted; waiting for both app clients to recover',flush=True)
                    time.sleep(.25)
                if test.returncode:
                    print((reports/'flutter.log').read_text(encoding='utf-8',errors='replace')[-8000:])
                    raise SystemExit(test.returncode)
                report=json.loads((reports/'report.json').read_text())
                with closing(sqlite3.connect(db)) as connection:
                    awards=dict(connection.execute('SELECT player,points FROM awards WHERE match_id=?',(report['match_id'],)))
                    assert awards==report['ranking_awards']
                    assert connection.execute('SELECT COUNT(*) FROM results WHERE match_id=?',(report['match_id'],)).fetchone()[0]==1
                assert restarted and report['backend_restarted'] and report['reconnected']
                assert report['identical_final_results'] and report['client_results'][0]==report['client_results'][1]
                report['persisted_awards_verified']=True
                (reports/'report.json').write_text(json.dumps(report,indent=2))
            finally:
                if test and test.poll() is None:test.terminate();test.wait(timeout=10)
                server.terminate();server_exit_codes.append(server.wait(timeout=10))
    report.update(flutter_exit_code=test.returncode,server_exit_codes=server_exit_codes,
                  controlled_servers_exited=server.poll() is not None,verification_complete=True)
    (reports/'report.json').write_text(json.dumps(report,indent=2))
    print(json.dumps({k:v for k,v in report.items() if k!='log'},indent=2))


if __name__=='__main__':main()

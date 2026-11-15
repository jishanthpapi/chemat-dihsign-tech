from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
import json
import sqlite3
import pytest
from fastapi.testclient import TestClient
from starlette.websockets import WebSocketDisconnect
from chemat.api import create_app
from chemat.engine import RuleError
from chemat.store import Store, AWARDS, season


@pytest.fixture
def setup(tmp_path):
    store=Store(tmp_path/'test.sqlite3',turn_seconds=15,negotiation_seconds=7)
    accounts=[store.register(name) for name in ['Alpha','Beta','Gamma','Delta']]
    ids=[a['player_id'] for a in accounts]
    code=store.lobby(ids[0])
    for pid in ids[1:]:
        store.join(pid,code)
    mid=store.start(ids[0],code,0)
    return store, accounts, mid


def headers(account):
    return {'X-Player-ID':account['player_id'],'X-Device-Credential':account['credential']}


def test_D4_unique_names_authenticated_ids_and_no_plaintext_credentials(setup):
    store, accounts, mid=setup
    a,b,*_=accounts
    with pytest.raises(RuleError):
        store.register(' ALPHA ')
    with pytest.raises(RuleError):
        store.rename(b['player_id'],'alpha')
    assert store.authenticate(a['player_id'],a['credential'])==a['player_id']
    with pytest.raises(RuleError):
        store.authenticate(a['player_id'],b['credential'])
    with store.db() as db:
        assert a['credential'] not in str([dict(r) for r in db.execute('SELECT * FROM players')])
    with TestClient(create_app(store,lambda:1,False)) as client:
        assert client.get(f'/matches/{mid}',headers={'X-Player-ID':a['player_id'],'X-Device-Credential':'bad'}).status_code==401
        assert client.get(f'/matches/{mid}',headers={'X-Player-ID':a['player_id']}).status_code==422


def test_D3_friend_request_requires_target_acceptance(setup):
    store, accounts, _=setup
    a,b,c,_=[x['player_id'] for x in accounts]
    store.friend_request(a,'beta')
    assert store.friends(a)[0]['accepted']==0
    with pytest.raises(RuleError):
        store.friend_accept(a,a)
    with pytest.raises(RuleError):
        store.friend_accept(c,a)
    store.friend_accept(b,a)
    assert store.friends(a)[0]['accepted']==1
    assert store.friends(b)==store.friends(a)


def test_D8_atomic_persistence_receipts_restart_and_versions(setup):
    store, accounts, mid=setup
    a=accounts[0]['player_id']
    initial=store.view(a,mid)
    current=initial['state']['current']
    result=store.command(current,mid,'end',0,'end_turn',{},1)
    assert result['version']==1
    reopened=Store(store.path)
    assert reopened.view(current,mid)==dict(version=1,state=result['state'])
    assert reopened.command(current,mid,'end',0,'end_turn',{},1)['duplicate']
    with pytest.raises(RuleError):
        store.command(current,mid,'end',1,'bank',{'amount':1},1)
    with pytest.raises(RuleError):
        store.command(current,mid,'stale',0,'end_turn',{},1)
    before=store.view(a,mid)
    with pytest.raises(RuleError):
        store.command(before['state']['current'],mid,'bad',1,'bank',{'amount':-1},1)
    assert store.view(a,mid)==before
    outsider=store.register('Outsider')['player_id']
    with pytest.raises(RuleError):
        store.command(outsider,mid,'bad',1,'end_turn',{},1)


def test_D8_simultaneous_commands_one_wins(setup):
    store, accounts, mid=setup
    current=store.view(accounts[0]['player_id'],mid)['state']['current']
    def attempt(i):
        try:
            return store.command(current,mid,str(i),0,'end_turn',{},1)['version']
        except RuleError:
            return 'conflict'
    with ThreadPoolExecutor(max_workers=2) as executor:
        results=list(executor.map(attempt,range(2)))
    assert sorted(map(str,results))==['1','conflict']


def test_D1_D2_rankings_verified_once_and_utc_month_reset(setup):
    store, accounts, mid=setup
    # Controlled authoritative terminal fixture; API does not accept results/placements.
    before=datetime(2026,11,30,23,59,59,tzinfo=timezone.utc).timestamp()
    after=before+1
    with store.db() as db:
        _,match=store._load(db,mid)
        for place,p in enumerate(match.players.values(),1):
            p.placement=place
            p.active=False
        match.phase='finished'
        store._save(db,mid,1,match,before)
        store._save(db,mid,2,match,after)
    board=store.leaderboard(before)
    assert sorted(x['ranking_points'] for x in board)==[0,5,15,30]
    assert store.leaderboard(after)==[]
    assert season(before)=='2026-11' and season(after)=='2026-12'
    reopened=Store(store.path)
    assert reopened.leaderboard(before)==board
    with store.db() as db:
        assert db.execute('SELECT COUNT(*) FROM awards').fetchone()[0]==4
        assert db.execute('SELECT COUNT(*) FROM results').fetchone()[0]==1


def test_unresolved_forfeit_results_never_ranked(setup):
    store, accounts, mid=setup
    with store.db() as db:
        _,match=store._load(db,mid)
        match.phase='finished'
        match.result_blocked=True
        store._save(db,mid,1,match,1)
    assert store.leaderboard(1)==[]


def test_D7_server_timers_cannot_be_bypassed(setup):
    store, accounts, mid=setup
    state=store.view(accounts[0]['player_id'],mid)
    pid=state['state']['current']
    assert state['state']['deadline']==15
    result=store.command(pid,mid,'late',0,'end_turn',{},15)
    assert result['expired'] and result['state']['current']!=pid
    with store.db() as db:
        _,match=store._load(db,mid)
        assert match.missed[pid]==1
        assert match.negotiation_seconds==7


def test_D5_durable_disconnect_reconnect_boundary(setup):
    store, accounts, mid=setup
    pid=store.view(accounts[0]['player_id'],mid)['state']['current']
    store.connection(pid,mid,0,False)
    reopened=Store(store.path)
    reopened.tick_all(89.99)
    assert reopened.view(pid,mid)['state']['current']==pid
    reopened.connection(pid,mid,90,True)
    assert reopened.view(pid,mid)['state']['deadline']==105
    reopened.connection(pid,mid,91,False)
    reopened.tick_all(181.001)
    assert reopened.view(pid,mid)['state']['current']!=pid
    reopened.connection(pid,mid,181.001,True)


def test_api_lobby_matchmaking_friend_and_username_flow(tmp_path):
    store=Store(tmp_path/'api.sqlite3')
    with TestClient(create_app(store,lambda:1,False)) as client:
        a=client.post('/players',json={'username':'one'}).json()
        b=client.post('/players',json={'username':'two'}).json()
        assert client.post('/players',json={'username':'ONE'}).status_code==409
        assert client.patch('/players/me',json={'username':'renamed'},headers=headers(a)).status_code==200
        assert client.post('/friends/request',json={'target':'two'},headers=headers(a)).status_code==200
        assert client.post('/friends/accept',json={'sender':a['player_id']},headers=headers(b)).status_code==200
        assert client.get('/friends',headers=headers(a)).json()[0]['accepted']==1
        code=client.post('/matchmaking',headers=headers(a)).json()['code']
        assert client.post('/matchmaking',headers=headers(b)).json()['code']==code
        for account in [a,b]:
            assert client.post(f'/lobbies/{code}/ready',headers=headers(account)).status_code==200
        mid=client.post(f'/lobbies/{code}/start',headers=headers(a)).json()['match_id']
        assert client.get(f'/lobbies/{code}',headers=headers(a)).json()['match_id']==mid
        initial=client.get(f'/matches/{mid}',headers=headers(a)).json()
        current=initial['state']['current']
        who=a if current==a['player_id'] else b
        response=client.post(f'/matches/{mid}/commands',headers=headers(who),json={'request_id':'one','version':0,'command':'end_turn'}).json()
        assert response['version']==1


def test_websocket_auth_redaction_command_broadcast_and_restore(setup):
    store, accounts, mid=setup
    a,b,*_=accounts
    with TestClient(create_app(store,lambda:1,False)) as client:
        with client.websocket_connect(f'/matches/{mid}/ws') as ws:
            ws.send_json(dict(player_id=a['player_id'],credential=a['credential']))
            first=ws.receive_json()
            assert 'task' in first['state']['players'][a['player_id']]
            assert 'task' not in first['state']['players'][b['player_id']]
            assert 'rng' not in str(first) and 'credential' not in str(first)
            ws.send_json({'request_id':'invalid','version':first['version'],'command':'create','args':{'compound':'Aspirin'}})
            assert 'error' in ws.receive_json()
            current=first['state']['current']
            account=next(x for x in accounts if x['player_id']==current)
            response=client.post(f'/matches/{mid}/commands',headers=headers(account),json={'request_id':'end','version':first['version'],'command':'end_turn'}).json()
            event=ws.receive_json()
            assert event['version']==response['version']
        with client.websocket_connect(f'/matches/{mid}/ws') as ws:
            ws.send_json(dict(player_id=a['player_id'],credential=a['credential']))
            assert ws.receive_json()['state']['current']==response['state']['current']
        with pytest.raises(WebSocketDisconnect):
            with client.websocket_connect(f'/matches/{mid}/ws') as ws:
                ws.send_json(dict(player_id=a['player_id'],credential=b['credential']))
                ws.receive_json()


def test_D8_pending_private_choice_survives_restart_and_late_response(setup):
    store,accounts,mid=setup
    actor=accounts[0]['player_id']
    # Controlled owned-action fixture, entered through production command path afterwards.
    with store.db() as db:
        version,match=store._load(db,mid)
        match.players[actor].hand['action']['Research Breakthrough']=1
        match.players[actor].pesos=10
        store._save(db,mid,version,match,0)
    request=0
    while True:
        state=store.view(actor,mid)
        if state['state']['phase']!='regular':
            break
        pid=state['state']['current']
        if pid==actor:
            store.command(pid,mid,str(request),state['version'],'play',{'card':'Research Breakthrough'},1)
            request+=1
            state=store.view(actor,mid)
        store.command(pid,mid,str(request),state['version'],'end_turn',{},1)
        request+=1
    reopened=Store(store.path)
    choice=reopened.view(actor,mid)['state']['choice']
    assert choice['mode']=='research'
    other=accounts[1]['player_id']
    assert reopened.view(other,mid)['state']['choice'] is None
    # Approved final amendment: mandatory selections now resolve automatically.
    reopened.tick_all(100)
    state=reopened.view(actor,mid)
    assert state['state']['phase']=='reaction'
    assert state['state']['choice'] is None
    assert any(e['event']=='choice.automatic' for e in state['state']['history'])


def test_api_rejects_client_supplied_results_and_persists_earned_result(setup):
    from collections import Counter
    store,accounts,mid=setup
    a,b,c,d=[x['player_id'] for x in accounts]
    # Near-finish fixture: only the compound intent and phase completion are external commands.
    with store.db() as db:
        _,match=store._load(db,mid)
        for place,pid in enumerate([a,b],1):
            match.players[pid].placement=place
            match.players[pid].active=False
        p=match.players[c]
        p.match_points=9
        p.task='Calcium carbonate'
        p.pesos=9
        p.hand['reactant']=Counter({'Calcium chloride':1,'Sodium carbonate':1})
        p.hand['apparatus']=Counter({'Beaker':1,'Stirring rod':1})
        match._start_reactions([c,d],0)
        store._save(db,mid,0,match,0)
    with pytest.raises(RuleError):
        store.command(c,mid,'fake',0,'result',{'placement':1},1)
    result=store.command(c,mid,'create',0,'create',{'compound':'Calcium carbonate'},1)
    assert result['state']['placements'][c]==3
    result=store.command(c,mid,'finish',1,'end_reaction',{},1)
    result=store.command(d,mid,'finish',2,'end_reaction',{},1)
    assert result['state']['phase']=='finished'
    assert sorted(row['ranking_points'] for row in store.leaderboard(1))==[0,5,15,30]

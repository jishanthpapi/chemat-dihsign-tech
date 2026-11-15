import pytest
from fastapi.testclient import TestClient
from chemat.api import create_app
from chemat.store import Store
from chemat.engine import RuleError


def test_lobby_capacity_readiness_leave_transfer_cancel_expire(tmp_path):
    s=Store(tmp_path/'lobby.db');ids=[s.register(f'p{i}')['player_id'] for i in range(5)]
    code=s.lobby(ids[0],now=10)
    for pid in ids[1:4]:s.join(pid,code)
    with pytest.raises(RuleError):s.join(ids[4],code)
    with pytest.raises(RuleError):s.start(ids[0],code,11,require_ready=True)
    with pytest.raises(RuleError):s.lobby(ids[1])
    s.lobby_change(ids[0],code,'leave')
    assert s.lobby_view(ids[1],code)['owner']==ids[1]
    s.lobby_change(ids[1],code,'cancel')
    assert s.lobby_view(ids[1],code)['status']=='cancelled'
    code=s.lobby(ids[0],now=20);s.tick_all(1820)
    assert s.lobby_view(ids[0],code)['status']=='expired'


def test_unicode_and_atomic_username_registration(tmp_path):
    from concurrent.futures import ThreadPoolExecutor
    s=Store(tmp_path/'names.db')
    def register(i):
        try:s.register('Café' if i==0 else 'Cafe\u0301');return True
        except RuleError:return False
    with ThreadPoolExecutor(2) as executor:
        assert sum(executor.map(register,range(2)))==1
    with pytest.raises(RuleError):s.register('bad\x00name')


def test_disconnected_lobby_host_lease_transfers_after_grace(tmp_path):
    s=Store(tmp_path/'presence.db')
    a,b=[s.register(name)['player_id'] for name in ('a','b')]
    code=s.lobby(a,now=1);s.join(b,code,now=2)
    s.lobby_view(b,code,now=80)
    s.tick_all(90)
    assert s.lobby_view(b,code,now=90)['owner']==a
    s.tick_all(91)
    assert s.lobby_view(b,code,now=91)['owner']==b


def test_registration_rate_limit_and_authenticated_private_endpoints(tmp_path):
    s=Store(tmp_path/'api.db')
    with TestClient(create_app(s,lambda:1,False)) as client:
        for i in range(30):assert client.post('/players',json={'username':f'name{i}'}).status_code==200
        assert client.post('/players',json={'username':'overflow'}).status_code==429
        assert client.get('/leaderboard/friends').status_code==422
        assert client.get('/players/search?q=a').status_code==422


def test_forfeit_zero_award_and_remaining_player_correct_place(tmp_path):
    s=Store(tmp_path/'ranks.db')
    ids=[s.register(f'p{i}')['player_id'] for i in range(2)]
    code=s.lobby(ids[0]);s.join(ids[1],code);mid=s.start(ids[0],code,0)
    with s.db() as db:
        _,m=s._load(db,mid)
        # Trusted rule fixture; public client cannot submit placements or final state.
        m.forfeit(ids[0],1);m._terminal();s._save(db,mid,1,m,1)
    assert {x['player']:x['ranking_points'] for x in s.leaderboard(1)}=={ids[0]:0,ids[1]:30}


def test_accepted_friend_filter_decline_remove(tmp_path):
    s=Store(tmp_path/'friends.db')
    a,b,c=[s.register(n)['player_id'] for n in ('a','b','c')]
    s.friend_request(a,b);s.friend_request(c,a)
    s.friend_accept(b,a)
    s.remove_friend(a,c)
    assert len(s.friends(a))==1 and s.friends(a)[0]['accepted']==1
    s.remove_friend(b,a)
    assert s.friends(a)==[]


def test_server_descriptions_cover_all_actions(tmp_path):
    with TestClient(create_app(Store(tmp_path/'help.db'),lambda:1,False)) as client:
        data=client.get('/catalog').json()
        assert len(data['action'])==29
        assert all(r['description'] and type(r['requires_target']) is bool for r in data['action'])

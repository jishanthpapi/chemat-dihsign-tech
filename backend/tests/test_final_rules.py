from collections import Counter
import pytest
from chemat.match import Match
from chemat.engine import RuleError


def test_forfeits_bottom_order_preserve_secured_and_timestamps():
    m=Match(list('abcd'),1,0)
    m.players['a'].match_points=10;m._placement('a')
    m.forfeit('b',10,'test');m.forfeit('c',10,'test')
    assert [m.players[p].placement for p in 'abc']==[1,4,3]
    assert m.forfeits['b']['sequence']<m.forfeits['c']['sequence']
    assert m.forfeits['b']['at']==10 and not m.players['b'].active
    m._terminal()
    assert m.players['d'].placement==2 and m.phase=='finished'


def test_forfeit_partial_settlement_single_lender_records_default():
    m=Match(list('ab'),1,0)
    m.players['a'].hand['apparatus']['Beaker']=1
    m.players['a'].pesos=9
    key=m.offer('a','b',{'pesos':9,'cards':[['apparatus','Beaker']]},{},0,1)
    m.accept('b',key,1)
    m.players['b'].pesos=3
    m.forfeit('b',2)
    assert not m.loans and m.loan_history[-1]['default_pesos']==6
    assert m.players['a'].hand['apparatus']['Beaker']==1
    assert m.players['b'].pesos==0


def test_multiple_lender_shortfall_settles_oldest_server_sequence_first():
    m=Match(list('abc'),1,0)
    for pid in 'ac':
        m.players[pid].pesos=5
        key=m.offer(pid,'b',{'pesos':5},{},0,1)
        m.accept('b',key,1)
    m.players['b'].pesos=1
    before_a=m.players['a'].pesos
    before_c=m.players['c'].pesos
    m.forfeit('b',2)
    assert m.players['a'].pesos==before_a+1 and m.players['c'].pesos==before_c
    assert not m.loans
    assert [l['default_pesos'] for l in m.loan_history]==[4,5]


def test_proposal_expiry_and_decline_no_transfers():
    m=Match(list('ab'),1,0)
    m.players['a'].pesos=5
    key=m.offer('a','b',{'pesos':2},{},0)
    m.tick(30)
    assert m.offers[key]['status']=='expired' and m.players['a'].pesos==5
    with pytest.raises(RuleError):m.accept('b',key,31)


def test_scanner_exact_instances_and_task():
    m=Match(list('ab'),1,0)
    p=m.players['a'];p.task='Calcium carbonate';p.pesos=9
    p.hand['reactant']=Counter({'Calcium chloride':1,'Sodium carbonate':1})
    p.hand['apparatus']=Counter({'Beaker':1,'Stirring rod':1})
    m._start_reactions(['a','b'],0)
    view=m.snapshot('a');ids=list(view['instances'])
    with pytest.raises(RuleError):m.command('a','scan',{'task_id':view['task_id'],'card_ids':ids+ids[:1]},1)
    with pytest.raises(RuleError):m.command('a','scan',{'task_id':'fake','card_ids':ids},1)
    m.command('a','scan',{'task_id':view['task_id'],'card_ids':ids},1)
    assert m.players['a'].match_points==1


def test_sessions_expiry_revocation_and_renewal(tmp_path):
    from chemat.store import Store
    s=Store(tmp_path/'auth.db');account=s.register('player')
    pid=account['player_id'];secret=account['credential']
    token=s.session(pid,secret,0)['access_token']
    assert s.authenticate(pid,token,899)==pid
    with pytest.raises(RuleError):s.authenticate(pid,token,900)
    renewed=s.session(pid,secret,901)['access_token']
    assert s.authenticate(pid,renewed,902)==pid
    s.revoke(pid)
    with pytest.raises(RuleError):s.authenticate(pid,renewed,903)
    with pytest.raises(RuleError):s.session(pid,secret,903)

"""Amendments A1–A17: controlled fixtures plus scheduler-driven regressions."""
from collections import Counter
import json
import pytest
from chemat.engine import Deck, RuleError, catalog
from chemat.match import Match


def game(count=3, seed=9):
    return Match(list('abcd')[:count], seed, 0, turn_seconds=60, negotiation_seconds=20)


def cmd(m, pid, name, **args):
    m.command(pid, name, args, 1)


def actions(m, plays):
    """Inject owned action cards, then use real regular turns and queue ordering."""
    for pid, name, target in plays:
        m.players[pid].hand['action'][name] += 1
        m.players[pid].pesos += 2
    while m.phase == 'regular':
        pid = m.current
        for actor, name, target in plays:
            if actor == pid:
                cmd(m,pid,'play',card=name,target=target)
        cmd(m,pid,'end_turn')


def finish_reactions(m):
    while m.phase == 'reaction':
        cmd(m,m.current,'end_reaction')


def loan(m, lender='a', borrower='b', cards=None, pesos=0, rounds=1):
    m.players[lender].pesos += pesos
    for k,n in cards or []:
        m.players[lender].hand[k][n] += 1
    key = m.offer(lender,borrower,{'cards':cards or [], 'pesos':pesos},{},1,rounds)
    m.accept(borrower,key,1)
    return key


def prepare_recipe(m, pid, name='Calcium carbonate', points=0):
    r = next(r for r in catalog()['task'] if r['name']==name)
    p = m.players[pid]
    p.task, p.match_points, p.pesos = name, points, 100
    p.hand['reactant'] = Counter(r['reactants'])
    p.hand['apparatus'] = Counter(r['apparatus'])
    return p


def test_A1_A4_same_named_card_substitution_and_borrower_order():
    m = game()
    first = loan(m,cards=[['apparatus','Beaker']])
    second = loan(m,pesos=2)
    m.repay('b',second)
    assert first in m.loans and second not in m.loans
    m.players['b'].hand['apparatus'] = Counter({'Stirring rod':1})
    with pytest.raises(RuleError):
        cmd(m,'b','repay',loan=first)
    with pytest.raises(RuleError):
        cmd(m,'b','repay',loan=first,substitute=True)
    with pytest.raises(RuleError):
        cmd(m,'b','substitute',loan=first,pesos=3)
    cmd(m,'a','substitute',loan=first,pesos=3)
    m.players['b'].pesos = 3
    cmd(m,'b','repay',loan=first,substitute=True)
    assert not m.loans
    assert m.players['b'].hand['apparatus']['Stirring rod']==1


def test_A2_A3_deadline_after_all_minis_and_lender_penalties():
    m = game()
    key = loan(m,pesos=2)
    actions(m,[('b','Double Reaction',None),('b','Double Reaction',None),('c','Double Reaction',None)])
    finish_reactions(m)
    expected_order = [p for p in m.order for _ in range({'b':2,'c':1}.get(p,0))]
    assert m.mini and m.current==expected_order[0] and m.completed_rounds==0
    for expected in expected_order:
        assert m.current==expected
        assert m.loans[key]['penalty']==0
        cmd(m,m.current,'end_turn')
        finish_reactions(m)
    assert m.completed_rounds==1 and m.loans[key]['penalty']==2
    actions(m,[])
    finish_reactions(m)
    assert m.loans[key]['penalty']==4
    before = m.players['a'].pesos
    m.players['b'].pesos = 6
    cmd(m,'b','repay',loan=key)
    assert m.players['a'].pesos==before+6


def test_A5_A6_placed_borrower_frozen_and_exited_lender_escrow():
    m = game()
    key = loan(m,pesos=2)
    m.players['a'].match_points=10
    m._placement('a')
    assert not m.players['a'].active
    m.players['b'].match_points=12
    m._placement('b')
    assert m.players['b'].active and m.players['b'].placement==2
    assert m.players['b'].match_points==10
    m.players['b'].pesos=5
    cmd(m,'b','repay',loan=key)
    assert not m.players['b'].active
    assert m.escrow['a']['pesos']==2
    assert m.players['b'].pesos==0


def test_A6_frozen_compounds_zero_reward_and_debt_stays():
    m = game()
    key = loan(m,pesos=2)
    actions(m,[])
    while m.current!='b':
        cmd(m,m.current,'end_reaction')
    p = prepare_recipe(m,'b',points=10)
    p.placement=1
    cmd(m,'b','create',compound=p.task)
    assert p.match_points==10 and p.active and key in m.loans


def test_A7_A8_optional_redirect_chain_terminates_and_consumes():
    m = game()
    m.players['a'].hand['apparatus']['Beaker']=1
    actions(m,[('b','Counter-Reaction',None),('b','Counter-Reaction',None),('c','Counter-Reaction',None),('a','Equipment Theft','b')])
    assert m.choice['mode']=='redirect' and m.choice['player']=='b'
    cmd(m,'b','choose',selected=['c'])
    assert m.defences['b']['Counter-Reaction']==1
    assert m.decks['action'].discard.count('Counter-Reaction')==1
    cmd(m,'c','choose',selected=['b'])
    # b cannot redirect this same attack twice, despite another defence copy.
    assert m.choice is None and m.phase=='reaction'
    assert m.defences['b']['Counter-Reaction']==1
    finish_reactions(m)
    assert m.defences['b']['Counter-Reaction']==0
    assert m.decks['action'].discard.count('Counter-Reaction')==3


def test_A7_decline_and_expiry():
    m = game()
    actions(m,[('b','Counter-Reaction',None),('b','Safety Goggles',None),('a','Lab Lockdown','b')])
    m.tick(22)
    assert m.phase=='reaction' and 'b' not in m.locked
    assert m.defences['b']['Counter-Reaction']==1
    assert m.defences['b']['Safety Goggles']==0


def test_A8_storage_before_counter_goggles_and_chaos_immune():
    m = game()
    m.players['b'].hand['reactant']['Water']=1
    actions(m,[('b','Secure Storage',None),('b','Counter-Reaction',None),('b','Safety Goggles',None),('a','Card Heist','b'),('a','Chemical Spill',None)])
    assert m.choice is None
    assert m.defences['b']['Counter-Reaction']==1 and m.defences['b']['Safety Goggles']==1
    assert m.players['b'].hand['reactant']['Water']==0


def test_A8_A9_backup_before_insurance_and_coexistence():
    m = game()
    m.players['b'].hand['reactant']=Counter({'Water':1,'Acetic acid':1})
    actions(m,[('b','Emergency Backup',None),('b','Lab Insurance',None),('a','Contamination!','b')])
    cmd(m,'b','choose',selected=[['reactant','Water'],['reactant','Acetic acid']])
    assert m.choice['mode']=='backup'
    cmd(m,'b','choose',selected=[['reactant','Water']])
    assert m.players['b'].hand['reactant']==Counter({'Water':1})
    assert m.defences['b']['Lab Insurance']==1


def test_A9_insurance_after_two_actual_losses():
    m = game()
    m.players['b'].hand['reactant']=Counter({'Water':2})
    actions(m,[('b','Lab Insurance',None),('a','Card Heist','b')])
    assert sum(m.players['b'].hand['reactant'].values())==2
    assert m.defences['b']['Lab Insurance']==0


def test_A10_attacker_selects_equipment():
    m = game()
    m.players['b'].hand['apparatus']=Counter({'Beaker':1,'Fume hood':1})
    actions(m,[('a','Equipment Theft','b')])
    assert m.choice['player']=='a'
    with pytest.raises(RuleError):
        cmd(m,'b','choose',selected=[['apparatus','Beaker']])
    cmd(m,'a','choose',selected=[['apparatus','Fume hood']])
    assert m.players['a'].hand['apparatus']['Fume hood']==1
    assert m.players['b'].hand['apparatus']['Beaker']==1


@pytest.mark.parametrize('copies',[1,2,3])
def test_A11_sequential_reversal_effective_next_round(copies):
    m = game()
    old = m.order[:]
    actions(m,[('a','Experiment Reversal',None)]*copies)
    assert m.order==old
    finish_reactions(m)
    assert m.order==(old[::-1] if copies%2 else old)


def test_A12_simultaneous_shuffle_empty_hands():
    m = game()
    old = m.order[:]
    m.players[old[0]].hand['apparatus']['Beaker']=1
    # Empty players must not re-pass a newly received card.
    actions(m,[(old[0],'Formula Shuffle',None)])
    assert m.players[old[1]].hand['apparatus']['Beaker']==1
    assert m.players[old[2]].hand['apparatus']['Beaker']==0


@pytest.mark.parametrize('available',range(6))
def test_A13_research_partial_supply(available):
    m = game()
    m.decks['reactant']=Deck(['Water']*available)
    actions(m,[('a','Research Breakthrough',None)])
    assert m.choice['count']==min(2,available)
    cmd(m,'a','choose',selected=[['reactant','Water']]*min(2,available))
    assert m.players['a'].hand['reactant']['Water']==min(2,available)
    assert m.decks['reactant'].discard==['Water']*max(0,available-2)


def test_A14_empty_task_supply_and_recovery():
    m = game()
    m.players[m.current].task=None
    waiting = m.current
    m.decks['task']=Deck([])
    actions(m,[])
    assert m.current==waiting and m.players[waiting].task is None
    with pytest.raises(RuleError):
        cmd(m,waiting,'create',compound='Calcium carbonate')
    m.decks['task'].discard.append('Calcium carbonate')
    finish_reactions(m)
    actions(m,[])
    assert m.players[waiting].task=='Calcium carbonate'


def test_A15_replacement_once_and_lifetime_escalation():
    m = game()
    actions(m,[])
    pid=m.current
    m.players[pid].pesos=100
    cmd(m,pid,'replace')
    assert m.players[pid].pesos==80
    for name,args in [('replace',{}),('create',{'compound':m.players[pid].task})]:
        with pytest.raises(RuleError):
            cmd(m,pid,name,**args)
    finish_reactions(m)
    actions(m,[])
    m.players[pid].pesos=100
    cmd(m,pid,'replace')
    assert m.players[pid].pesos==75


def test_A16_cutoff_at_creation_atomic_failures_and_all_pass_boundary():
    m = game()
    actions(m,[])
    pid=m.current
    p = prepare_recipe(m,pid)
    cmd(m,'b','bank',amount=1)
    with pytest.raises(RuleError):
        cmd(m,pid,'create',compound='Aspirin')
    assert m.economy_open
    cmd(m,pid,'create',compound=p.task)
    with pytest.raises(RuleError):
        cmd(m,'b','bank',amount=1)
    with pytest.raises(RuleError):
        cmd(m,'b','offer',target='a',give={},receive={})
    finish_reactions(m)
    actions(m,[('b','Double Reaction',None)])
    assert m.economy_open
    finish_reactions(m)
    assert m.mini and m.phase=='regular'  # old window closes, new regular window opens


def test_A17_unlimited_bank_and_state_roundtrip():
    m = game()
    m.bank_net=-10**30
    before=m.players['a'].pesos
    m._income(m.players['a'])
    assert m.players['a'].pesos>before
    restored=Match.from_state(json.loads(json.dumps(m.to_state())))
    assert restored.to_state()==m.to_state()
    m._income(m.players['a'])
    restored._income(restored.players['a'])
    assert restored.to_state()==m.to_state()


def test_miniround_actions_wait_next_shared_resolution():
    m=game()
    actions(m,[('b','Double Reaction',None)])
    finish_reactions(m)
    m.players['b'].pesos+=2
    m.players['b'].hand['action']['Double Reaction']=1
    cmd(m,'b','play',card='Double Reaction')
    cmd(m,'b','end_turn')
    finish_reactions(m)
    assert m.round==2 and not m.mini and len(m.pending)==1
    actions(m,[])
    finish_reactions(m)
    assert m.mini and m.current=='b'


def test_double_yield_stack_and_expire():
    m=game()
    actions(m,[('a','Double Yield',None)]*2)
    while m.current!='a':
        cmd(m,m.current,'end_reaction')
    p=prepare_recipe(m,'a')
    cmd(m,'a','create',compound=p.task)
    assert p.match_points==4
    finish_reactions(m)
    assert not m.yields


def test_D5_D6_D7_reconnect_grace_and_missed_streak():
    m=game(2)
    pid=m.current
    m.disconnect(pid,0)
    m.tick(60)
    assert m.current==pid and m.missed[pid]==0
    m.reconnect(pid,90)
    m.disconnect(pid,91)
    m.tick(181.01)
    assert m.missed[pid]==1
    m.reconnect(pid,181.01)
    # Drive scheduler with server time until the third missed regular turn.
    now=200
    for _ in range(30):
        if m.phase=='finished':
            break
        if m.phase=='regular' and m.current!=pid:
            m.end_turn(m.current,now)
        else:
            m.tick(now)
        now+=100
    assert m.players[pid].forfeited and m.missed[pid]==3 and m.players[pid].placement==2


def test_missed_streak_reset_and_positive_timers():
    m=game()
    m.missed[m.current]=2
    pid=m.current
    cmd(m,pid,'end_turn')
    assert m.missed[pid]==0
    with pytest.raises(RuleError):
        Match(['a','b'],1,0,turn_seconds=0)


def test_invalid_command_rolls_back_rng_and_all_state():
    m=game()
    state=m.to_state()
    with pytest.raises(RuleError):
        cmd(m,m.current,'offer',target='b',give={'pesos':-1})
    assert m.to_state()==state


def test_own_turn_debt_settlement_advances_exited_player():
    m=game()
    borrower=m.current
    lender=next(p for p in m.order if p!=borrower)
    key=loan(m,lender,borrower,pesos=2)
    m.players[borrower].match_points=10
    m._placement(borrower)
    cmd(m,borrower,'repay',loan=key)
    assert not m.players[borrower].active and m.current!=borrower


def test_debt_free_winner_retains_overshoot_score():
    m=game()
    m.players['a'].match_points=13
    m._placement('a')
    assert not m.players['a'].active and m.players['a'].match_points==13


def test_A5_card_repayment_to_exited_lender_escrow():
    m=game()
    key=loan(m,cards=[['apparatus','Beaker']])
    m.players['a'].match_points=10
    m._placement('a')
    cmd(m,'b','repay',loan=key)
    assert m.escrow['a']['cards']==[['apparatus','Beaker']]


def test_A9_redirected_area_attack_insurance_aggregates_actual_losses():
    m=game()
    m.players['c'].hand['reactant']=Counter({'Water':2})
    actions(m,[('b','Counter-Reaction',None),('c','Lab Insurance',None),('a','Supply Shortage',None)])
    # Targets follow normal order, so c's independent portion may be first.
    while m.choice and m.choice['mode']!='redirect':
        cmd(m,m.choice['player'],'choose',selected=m.choice['options'][:m.choice['count']])
    cmd(m,'b','choose',selected=['c'])
    while m.choice:
        cmd(m,m.choice['player'],'choose',selected=m.choice['options'][:m.choice['count']])
    assert m.defences['c']['Lab Insurance']==0
    assert sum(m.players['c'].hand['reactant'].values())==2


def test_mini_trade_initiation_and_negotiation_expiry():
    m=game()
    actions(m,[('b','Double Reaction',None)])
    finish_reactions(m)
    with pytest.raises(RuleError):
        cmd(m,'a','offer',target='b',give={})
    key=m.offer('b','a',{}, {},1)
    with pytest.raises(RuleError):
        m.accept('a',key,21)


@pytest.mark.parametrize('name,kind,expected', [('Quick Experiment','reactant',2),('Extra Equipment','apparatus',1)])
def test_good_draw_effects(name,kind,expected):
    m=game()
    actions(m,[('a',name,None)])
    assert sum(m.players['a'].hand[kind].values())==expected


@pytest.mark.parametrize('name,kind', [('Perfect Match','reactant'),('Lab Upgrade','apparatus')])
def test_chosen_discard_recovery(name,kind):
    m=game()
    card=m.decks[kind].cards.pop()
    m.decks[kind].discard.append(card)
    actions(m,[('a',name,None)])
    cmd(m,'a','choose',selected=[[kind,card]])
    assert m.players['a'].hand[kind][card]==1
    assert card not in m.decks[kind].discard


def test_chemical_discovery_and_lucky_task_exclusion():
    m=game()
    actions(m,[('a','Chemical Discovery',None),('a','Lucky Reaction',None)])
    assert m.choice['mode']=='discard'
    cmd(m,'a','choose',selected=m.choice['options'][:1])
    assert sum(m.players['a'].hand['reactant'].values())==2
    assert 'task' not in m.choice['options']
    cmd(m,'a','choose',selected=['apparatus'])
    assert sum(m.players['a'].hand['apparatus'].values())==1


def test_chaos_swap_and_recall_ignore_defences_and_exclude_tasks():
    m=game()
    m.players['a'].hand['reactant']=Counter({'Water':2})
    m.players['b'].hand['apparatus']=Counter({'Beaker':2})
    task=m.players['b'].task
    actions(m,[('b','Secure Storage',None),('b','Safety Goggles',None),('a','Market Swap','b'),('a','Equipment Recall',None)])
    cmd(m,'a','choose',selected=[['reactant','Water']]*2)
    assert m.players['a'].hand['apparatus']['Beaker']==2
    assert m.choice['mode']=='recall' and m.choice['player']=='a'
    cmd(m,'a','choose',selected=[['apparatus','Beaker']])
    assert m.players['a'].hand['apparatus']['Beaker']==1
    assert m.players['b'].task==task
    assert m.defences['b']['Safety Goggles']==1


def test_catalyst_and_mass_production():
    m=game()
    actions(m,[('a','Unexpected Catalyst','b'),('a','Mass Production',None)])
    assert [sum(m.players[p].hand['reactant'].values()) for p in 'abc']==[5,3,1]


@pytest.mark.parametrize('name,kind,card', [('Reactant Raid','reactant','Water'),('Stolen Research','action','Quick Experiment'),('Failed Experiment','reactant','Water')])
def test_remaining_attacks(name,kind,card):
    m=game()
    m.players['b'].hand[kind][card]=1
    actions(m,[('a',name,'b')])
    if m.choice:
        cmd(m,'a','choose',selected=[[kind,card]])
    assert m.players['b'].hand[kind][card]==0
    if name=='Failed Experiment':
        assert card in m.decks[kind].discard
    else:
        assert m.players['a'].hand[kind][card]==1


def test_lockdown_expires_before_personal_reaction():
    m=game()
    actions(m,[('a','Lab Lockdown','b'),('b','Double Reaction',None)])
    while m.current!='b':
        cmd(m,m.current,'end_reaction')
    p=prepare_recipe(m,'b')
    with pytest.raises(RuleError):
        cmd(m,'b','create',compound=p.task)
    finish_reactions(m)
    cmd(m,'b','end_turn')
    cmd(m,'b','create',compound=p.task)
    assert m.players['b'].match_points==1

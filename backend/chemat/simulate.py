"""Headless legal-command agent. Never injects cards, money or results."""
from collections import Counter
import json
from .match import Match


def inventory(match):
    total=Counter()
    for kind,deck in match.decks.items():
        total.update((kind,c) for c in deck.cards+deck.discard)
    for p in match.players.values():
        if p.task:
            total['task',p.task]+=1
        for kind,hand in p.hand.items():
            total.update({(kind,c):n for c,n in hand.items()})
    for action in match.pending+match.resolving:
        total['action',action['name']]+=1
    for defence in match.defences.values():
        total.update({('action',name):n for name,n in defence.items()})
    return +total


def simulate(seed=7, players=3, budget=5000):
    match=Match([f'agent-{i}' for i in range(players)],seed,0)
    original=inventory(match)
    commands=0

    def execute(pid, name, **args):
        nonlocal commands
        match.command(pid,name,args,0)
        commands+=1

    while match.phase!='finished' and commands<budget:
        pid=match.current
        p=match.players[pid]
        recipe=next((r for r in match.data['task'] if r['name']==p.task),None)
        if match.phase=='regular':
            if recipe:
                for kind,key in [('reactant','reactants'),('apparatus','apparatus')]:
                    needed=Counter(recipe[key])-p.hand[kind]
                    for name,amount in needed.items():
                        for other in match.active():
                            if other==pid:
                                continue
                            n=min(amount,match.players[other].hand[kind][name])
                            if n:
                                execute(other,'offer',target=pid,give={'cards':[[kind,name]]*n})
                                execute(pid,'accept',offer=str(match.sequence))
                                amount-=n
                    while Counter(recipe[key])-p.hand[kind] and p.pesos>recipe['fee'] and (match.decks[kind].cards or match.decks[kind].discard):
                        execute(pid,'buy',kind=kind)
            execute(pid,'end_turn')
        elif match.phase=='reaction':
            if recipe and all(not (Counter(recipe[key])-p.hand[kind]) for kind,key in [('reactant','reactants'),('apparatus','apparatus')]) and p.pesos>=recipe['fee']:
                execute(pid,'create',compound=p.task)
            execute(pid,'end_reaction')
        else:
            raise AssertionError(f'Unexpected simulation phase: {match.phase}')
        assert inventory(match)==original, 'Card conservation violated'
        assert sum(p.pesos+p.savings for p in match.players.values())+match.bank_net==0, 'Peso conservation violated'
    if match.phase!='finished':
        raise AssertionError(f'Seed {seed} exceeded {budget} commands at round {match.round}')
    result=dict(seed=seed,players=players,commands=commands,rounds=match.completed_rounds,
                placements={p:x.placement for p,x in match.players.items()},
                match_points={p:x.match_points for p,x in match.players.items()})
    assert sorted(result['placements'].values())==list(range(1,players+1))
    return result


if __name__=='__main__':
    print(json.dumps([simulate(seed,players) for players in (2,3,4) for seed in (7,19)],indent=2))

from collections import Counter
from copy import deepcopy
import pytest
from chemat.engine import Game, Deck, ReactionOpportunity, RuleError, catalog


def test_catalog():
    data = catalog()
    assert {k: sum(r['copies'] for r in data[k]) for k in ('reactant', 'apparatus', 'task', 'action')} == dict(reactant=82, apparatus=30, task=35, action=64)
    assert [len(data[k]) for k in ('reactant', 'apparatus', 'task', 'action')] == [29, 7, 20, 29]
    assert Counter({c: sum(r['copies'] for r in data['action'] if r['category'] == c) for c in ('good', 'attack', 'defence', 'chaos')}) == dict(good=19, attack=18, defence=11, chaos=16)
    for r in data['task']:
        assert r['fee'] == 5 + len(r['reactants']) + len(r['apparatus'])
        assert set(r['reactants']) <= {x['name'] for x in data['reactant']}
        assert set(r['apparatus']) <= {x['name'] for x in data['apparatus']}


@pytest.mark.parametrize('ids', [[], ['a'], ['a', 'a'], list('abcde'), ['', 'b']])
def test_player_count(ids):
    with pytest.raises(RuleError):
        Game(ids, 7)


@pytest.mark.parametrize('count', [2, 3, 4])
def test_setup(count):
    game = Game(list('abcd')[:count], 7)
    assert sum(len(d.cards) for d in game.decks.values()) + count == 211
    assert len(game.decks['task'].cards) == 35-count
    assert all(p.task and 1 <= p.pesos <= (12 if p.id == game.current else 6) for p in game.players.values())
    assert sum(p.pesos for p in game.players.values()) + game.bank_net == 0
    assert game.snapshot('a') == Game(list('abcd')[:count], 7).snapshot('a')
    assert 'task' not in game.snapshot('a')['players']['b']
    assert 'hand' not in game.snapshot('a')['players']['b']


def test_decks():
    game = Game(['a', 'b'], 1)
    deck = Deck([], ['x', 'y'])
    assert {deck.draw(game.rng), deck.draw(game.rng)} == {'x', 'y'}
    assert deck.draw(game.rng) is None
    assert deck.discard == []


@pytest.mark.parametrize('kind,fee', [('reactant', 1), ('apparatus', 1), ('action', 2)])
def test_purchase(kind, fee):
    game = Game(['a', 'b'], 1)
    p = game.players[game.current]
    p.pesos = 5
    top = game.decks[kind].cards[-1]
    assert game.buy(p.id, kind) == top
    assert p.hand[kind][top] == 1 and p.pesos == 5-fee
    with pytest.raises(RuleError):
        game.buy(next(x for x in game.players if x != p.id), kind)
    with pytest.raises(RuleError):
        game.buy(p.id, 'task')
    p.pesos = 0
    with pytest.raises(RuleError):
        game.buy(p.id, kind)
    p.pesos = 5
    game.decks[kind] = Deck([])
    with pytest.raises(RuleError):
        game.buy(p.id, kind)
    assert p.pesos == 5
    game.phase = 'reaction'
    with pytest.raises(RuleError):
        game.buy(p.id, kind)


def fixture(recipe):
    game = Game(['a', 'b'], 4)
    # Controlled unit fixture, not a legal gameplay path: never exposed by an API.
    game.phase = 'reaction'
    p = game.players['a']
    p.task, p.pesos = recipe['name'], recipe['fee']
    p.hand['reactant'] = Counter(recipe['reactants'])
    p.hand['apparatus'] = Counter(recipe['apparatus'])
    return game, p, ReactionOpportunity('a')


@pytest.mark.parametrize('recipe', catalog()['task'], ids=lambda r: r['name'])
def test_all_recipes(recipe):
    game, p, opportunity = fixture(recipe)
    assert opportunity.create(game, 'a', recipe['name']) == recipe['points']
    assert p.match_points == recipe['points'] and p.pesos == 0 and p.task is None
    assert not p.hand['reactant'] and not p.hand['apparatus']
    assert game.decks['reactant'].discard == recipe['reactants']
    assert game.decks['apparatus'].discard == recipe['apparatus']
    assert game.decks['task'].discard[-1] == recipe['name']
    opportunity.finish(game)
    assert p.task is not None
    with pytest.raises(RuleError):
        opportunity.create(game, 'a', p.task)


@pytest.mark.parametrize('fault', ['regular', 'action_resolution', 'wrong_player', 'wrong_task', 'reactant', 'apparatus', 'pesos', 'used'])
def test_rejections_atomic(fault):
    recipe = catalog()['task'][0]
    game, p, opportunity = fixture(recipe)
    who, task = 'a', recipe['name']
    if fault in ('regular', 'action_resolution'):
        game.phase = fault
    elif fault == 'wrong_player':
        who = 'b'
    elif fault == 'wrong_task':
        task = 'Aspirin'
    elif fault in ('reactant', 'apparatus'):
        p.hand[fault].clear()
    elif fault == 'pesos':
        p.pesos -= 1
    elif fault == 'used':
        opportunity.used = True
    before = deepcopy((game.players, game.decks, game.bank_net, opportunity))
    with pytest.raises(RuleError):
        opportunity.create(game, who, task)
    assert (game.players, game.decks, game.bank_net, opportunity) == before


def test_health():
    from fastapi.testclient import TestClient
    from chemat.api import app
    assert TestClient(app).get('/health').json()['multiplayer_ready'] is False

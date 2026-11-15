"""Milestone 1 primitives; no full-round orchestration or action resolution yet."""
from collections import Counter
from dataclasses import dataclass, field
import json
from pathlib import Path
import random

ROOT = Path(__file__).resolve().parents[2]
KINDS = ('reactant', 'apparatus', 'task', 'action')


class RuleError(ValueError):
    pass


def catalog():
    return json.loads(Path(__file__).with_name('catalog.json').read_text(encoding='utf-8'))


@dataclass
class Deck:
    cards: list[str]
    discard: list[str] = field(default_factory=list)

    def draw(self, rng):
        if not self.cards and self.discard:
            self.cards, self.discard = self.discard, []
            rng.shuffle(self.cards)
        return self.cards.pop() if self.cards else None


@dataclass
class Player:
    id: str
    pesos: int = 0
    savings: int = 0
    match_points: int = 0
    task: str | None = None
    placement: int | None = None
    active: bool = True
    forfeited: bool = False
    replacements: int = 0
    hand: dict = field(default_factory=lambda: {k: Counter() for k in ('reactant', 'apparatus', 'action')})


class Game:
    def __init__(self, player_ids, seed):
        if not 2 <= len(player_ids) <= 4 or len(set(player_ids)) != len(player_ids):
            raise RuleError('Require 2–4 unique players')
        if any(not isinstance(p, str) or not p.strip() for p in player_ids):
            raise RuleError('Player IDs must be nonempty strings')
        self.rng = random.Random(seed)
        self.data = catalog()
        self.decks = {}
        for kind in KINDS:
            cards = [r['name'] for r in self.data[kind] for _ in range(r['copies'])]
            self.rng.shuffle(cards)
            self.decks[kind] = Deck(cards)
        self.players = {p: Player(p) for p in player_ids}
        self.order = list(player_ids)
        self.rng.shuffle(self.order)
        # Bank tracks net flows, not a fictional finite starting supply (§5 gives none).
        self.bank_net = 0
        for p in self.players.values():
            self._income(p)
            p.task = self.decks['task'].draw(self.rng)
        self.current = self.order[0]
        self.phase = 'regular'
        self._income(self.players[self.current])

    def _income(self, player):
        amount = self.rng.randint(1, 6)
        player.pesos += amount
        self.bank_net -= amount

    def buy(self, player_id, kind):
        if self.phase != 'regular' or player_id != self.current:
            raise RuleError('Purchase requires own regular turn')
        if kind not in ('reactant', 'apparatus', 'action'):
            raise RuleError('Tasks cannot be purchased')
        player = self.players[player_id]
        fee = 2 if kind == 'action' else 1
        if player.pesos < fee:
            raise RuleError('Insufficient pesos')
        deck = self.decks[kind]
        if not deck.cards and not deck.discard:
            raise RuleError('No cards available')
        card = deck.draw(self.rng)
        player.pesos -= fee
        self.bank_net += fee
        player.hand[kind][card] += 1
        return card

    def snapshot(self, viewer):
        if viewer not in self.players:
            raise RuleError('Unknown viewer')
        return dict(phase=self.phase, current=self.current, order=self.order[:], players={
            pid: dict(pesos=p.pesos, match_points=p.match_points, active=p.active, forfeited=p.forfeited,
                      **({'task': p.task, 'savings': p.savings, 'replacements': p.replacements,
                          'hand': {k: dict(v) for k, v in p.hand.items()}} if pid == viewer else {}))
            for pid, p in self.players.items()},
            decks={k: dict(remaining=len(d.cards), discard=d.discard[:]) for k, d in self.decks.items()})


@dataclass
class ReactionOpportunity:
    """Server-owned context for one opportunity, not a client-supplied request.

    Full scheduler, multipliers, loans and placement are deliberately deferred.
    """
    player_id: str
    phase: str = 'reaction'
    used: bool = False

    def create(self, game, player_id, compound):
        if game.phase != 'reaction' or self.phase != 'reaction' or self.used or player_id != self.player_id:
            raise RuleError('Not an available reaction opportunity')
        player = game.players[player_id]
        if player.task != compound:
            raise RuleError('Compound must match active task')
        recipe = next((r for r in game.data['task'] if r['name'] == compound), None)
        if recipe is None:
            raise RuleError('Unknown compound')
        for kind, key in [('reactant', 'reactants'), ('apparatus', 'apparatus')]:
            if Counter(recipe[key]) - player.hand[kind]:
                raise RuleError('Missing ' + kind + ' cards')
        if player.pesos < recipe['fee']:
            raise RuleError('Insufficient pesos')
        # Validate entirely before mutating resources or opportunity.
        for kind, key in [('reactant', 'reactants'), ('apparatus', 'apparatus')]:
            for card in recipe[key]:
                player.hand[kind][card] -= 1
                if player.hand[kind][card] == 0:
                    del player.hand[kind][card]
                game.decks[kind].discard.append(card)
        player.pesos -= recipe['fee']
        game.bank_net += recipe['fee']
        points = 0 if player.placement is not None else recipe['points']
        player.match_points += points
        game.decks['task'].discard.append(compound)
        player.task = None
        self.used = True
        return points

    def finish(self, game):
        if self.phase != 'reaction':
            raise RuleError('Opportunity already closed')
        player = game.players[self.player_id]
        if self.used:
            player.task = game.decks['task'].draw(game.rng)
        self.phase = 'closed'

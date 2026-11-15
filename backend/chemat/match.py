"""Amended server-owned match scheduler. Choices are explicit, never client state."""
from collections import Counter
from copy import deepcopy
from dataclasses import asdict

from .engine import Game, Player, Deck, ReactionOpportunity, RuleError, catalog


def require(condition, message):
    if not condition:
        raise RuleError(message)


def positive(value):
    require(type(value) is int and value > 0, 'Expected positive integer')
    return value


class Match(Game):
    def __init__(self, player_ids, seed, now, turn_seconds=60, negotiation_seconds=30):
        super().__init__(player_ids, seed)
        self.turn_seconds = positive(turn_seconds)
        self.negotiation_seconds = positive(negotiation_seconds)
        self.round = 1
        self.completed_rounds = 0
        self.turn_list = self.order[:]
        self.reaction_list = []
        self.mini = False
        self.mini_queue = []
        self.extras = Counter()
        self.pending = []
        self.resolving = []
        self.defences = {p: Counter() for p in self.players}
        self.yields = Counter()
        self.locked = []
        self.reverse_count = 0
        self.economy_open = True
        self.opportunity = None
        self.replaced = False
        self.loans = {}
        self.offers = {}
        self.escrow = {p: {'pesos': 0, 'cards': []} for p in self.players}
        self.choice = None
        self.attack = None
        self.sequence = 0
        self.deadline = now + self.turn_seconds
        self.disconnected = {}
        self.missed = {p: 0 for p in self.players}
        self.result_blocked = False
        self.started_at=now
        self.finished_at=None
        self.history = []
        self.loan_history = []
        self.forfeits = {}
        self.card_ids = {p: {} for p in self.players}
        self.instance_sequence = 0
        self.task_ids = {p: {'name': x.task, 'id': f'task-{p}-0'} for p,x in self.players.items()}

    def event(self, name, now, **details):
        sequence=self.history[-1]['sequence']+1 if self.history else 1
        self.history.append(dict(sequence=sequence, event=name, at=now, **details))
        self.history=self.history[-100:]

    def _sync_instances(self):
        for pid in self.players:
            counts = Counter(map(tuple,self._cards(pid)))
            previous = self.card_ids[pid]
            kept = {}
            for key, card in previous.items():
                if counts[tuple(card)] > 0:
                    kept[key] = card
                    counts[tuple(card)] -= 1
            for card,n in counts.items():
                for _ in range(n):
                    self.instance_sequence += 1
                    kept[f'card-{self.instance_sequence}'] = list(card)
            self.card_ids[pid] = kept
            if self.task_ids[pid]['name'] != self.players[pid].task:
                self.instance_sequence += 1
                self.task_ids[pid] = {'name': self.players[pid].task, 'id': f'task-{self.instance_sequence}'}

    def scan(self, pid, task_id, selected):
        self._sync_instances()
        require(task_id == self.task_ids[pid]['id'], 'Active Task changed')
        require(isinstance(selected,list) and len(selected)==len(set(selected)), 'Select each card instance once')
        require(all(key in self.card_ids[pid] for key in selected), 'Card instance not owned')
        recipe = next((r for r in self.data['task'] if r['name']==self.players[pid].task), None)
        require(recipe is not None, 'No active Task')
        required = Counter([('reactant',c) for c in recipe['reactants']]+[('apparatus',c) for c in recipe['apparatus']])
        require(Counter(tuple(self.card_ids[pid][key]) for key in selected)==required, 'Selected cards must exactly match recipe')
        self.create(pid,recipe['name'])
        for key in selected:
            self.card_ids[pid].pop(key,None)

    def active(self):
        return [p for p in self.order if self.players[p].active]

    def _own(self, pid, phase):
        require(pid in self.players and self.players[pid].active, 'Inactive player')
        require(self.current == pid and self.phase == phase, 'Wrong turn or phase')

    def _window(self, pid, initiator=False):
        require(pid in self.players and self.players[pid].active, 'Inactive player')
        require(self.phase in ('regular', 'reaction') and self.economy_open, 'Economy window closed')
        if self.mini and initiator:
            require(pid == self.current, 'Only mini-round player may initiate')

    def _pay(self, pid, amount):
        require(self.players[pid].pesos >= amount, 'Insufficient pesos')
        self.players[pid].pesos -= amount
        self.bank_net += amount

    def _cards(self, pid, kinds=('reactant', 'apparatus', 'action')):
        return [[kind, name] for kind in kinds for name, n in self.players[pid].hand[kind].items() for _ in range(n)]

    def _take(self, pid, card):
        kind, name = card
        hand = self.players[pid].hand[kind]
        require(hand[name] > 0, 'Card unavailable')
        hand[name] -= 1
        if not hand[name]:
            del hand[name]

    def _give(self, pid, card):
        self.players[pid].hand[card[0]][card[1]] += 1

    def _discard(self, pid, card):
        self._take(pid, card)
        self.decks[card[0]].discard.append(card[1])

    def _draw(self, pid, kind, n):
        for _ in range(n):
            card = self.decks[kind].draw(self.rng)
            if card is not None:
                self._give(pid, [kind, card])

    def _ask(self, pid, mode, options, count, now, context=None):
        self.choice = dict(player=pid, mode=mode, options=options, count=count,
                           context=context or {}, deadline=now + self.negotiation_seconds)

    def bank(self, pid, amount, withdraw=False):
        self._window(pid)
        positive(amount)
        p = self.players[pid]
        if withdraw:
            require(p.savings >= amount, 'Insufficient savings')
            p.savings -= amount
            p.pesos += amount
        else:
            require(p.pesos >= amount + 1, 'Deposit requires amount plus 1 peso')
            self._pay(pid, 1)
            p.pesos -= amount
            p.savings += amount

    def offer(self, pid, target, give, receive, now, loan_rounds=None):
        self._window(pid, initiator=True)
        self._window(target)
        require(pid != target, 'Choose another player')
        for resources in (give, receive):
            require(set(resources) <= {'pesos', 'cards'}, 'Unknown resources')
            require(type(resources.get('pesos', 0)) is int and resources.get('pesos', 0) >= 0, 'Invalid pesos')
            for card in resources.get('cards', []):
                require(isinstance(card, list) and len(card) == 2 and card[0] in ('reactant', 'apparatus', 'action'), 'Invalid card')
                require(card[1] in {r['name'] for r in self.data[card[0]]}, 'Unknown card')
        if loan_rounds is not None:
            positive(loan_rounds)
            require(not receive.get('cards') and not receive.get('pesos'), 'Loan must not include reciprocal resources')
            require(give.get('cards') or give.get('pesos'), 'Empty loan')
        self.sequence += 1
        key = str(self.sequence)
        self.offers[key] = dict(sender=pid, target=target, give=deepcopy(give), receive=deepcopy(receive),
                                rounds=loan_rounds, deadline=now + self.negotiation_seconds, status='pending')
        return key

    def _can_transfer(self, pid, resources):
        require(self.players[pid].pesos >= resources.get('pesos', 0), 'Insufficient pesos')
        require(not (Counter(map(tuple, resources.get('cards', []))) - Counter(map(tuple, self._cards(pid)))), 'Missing offered cards')

    def _transfer(self, sender, target, resources):
        amount = resources.get('pesos', 0)
        self.players[sender].pesos -= amount
        if self.players[target].active:
            self.players[target].pesos += amount
        else:
            self.escrow[target]['pesos'] += amount
        for card in resources.get('cards', []):
            self._take(sender, card)
            if self.players[target].active:
                self._give(target, card)
            else:
                self.escrow[target]['cards'].append(card)

    def accept(self, pid, key, now):
        offer = self.offers.get(key)
        require(offer is not None and offer['target'] == pid, 'Not your offer')
        require(offer.get('status','pending') == 'pending', 'Offer no longer pending')
        require(now < offer['deadline'], 'Offer expired')
        self._window(offer['sender'], initiator=True)
        self._window(pid)
        self._can_transfer(offer['sender'], offer['give'])
        self._can_transfer(pid, offer['receive'])
        self._transfer(offer['sender'], pid, offer['give'])
        self._transfer(pid, offer['sender'], offer['receive'])
        if offer['rounds'] is not None:
            self.loans[key] = dict(lender=offer['sender'], borrower=pid,
                                   cards=deepcopy(offer['give'].get('cards', [])),
                                   pesos=offer['give'].get('pesos', 0), penalty=0,
                                   due=self.round + offer['rounds'] - 1, substitution=None)
        offer['status'] = 'accepted'

    def decline(self, pid, key):
        offer = self.offers.get(key)
        require(offer is not None and offer['target']==pid and offer.get('status')=='pending', 'Not a pending incoming offer')
        offer['status']='declined'

    def substitute(self, pid, key, pesos):
        loan = self.loans.get(key)
        require(loan is not None and loan['lender'] == pid, 'Only lender may approve substitution')
        require(type(pesos) is int and pesos >= 0 and loan['cards'], 'Invalid substitution')
        # Borrower consents by explicitly selecting substitution when repaying.
        loan['substitution'] = pesos

    def repay(self, pid, key, substitute=False):
        self._window(pid, initiator=True)
        loan = self.loans.get(key)
        require(loan is not None and loan['borrower'] == pid, 'Not your debt')
        require(not substitute or loan['substitution'] is not None, 'Lender has not approved substitution')
        resources = dict(pesos=loan['pesos'] + loan['penalty'] + (loan['substitution'] if substitute else 0),
                         cards=[] if substitute else loan['cards'])
        self._can_transfer(pid, resources)
        self._transfer(pid, loan['lender'], resources)
        self.loan_history.append(dict(id=key, **deepcopy(loan), status='repaid'))
        del self.loans[key]
        self._exit_if_ready(pid)

    def _exit_if_ready(self, pid):
        p = self.players[pid]
        if p.placement is None or any(l['borrower'] == pid for l in self.loans.values()):
            return
        p.active = False
        self.bank_net += p.pesos + p.savings
        p.pesos = p.savings = 0
        for card in self._cards(pid):
            self._discard(pid, card)
        if p.task:
            self.decks['task'].discard.append(p.task)
            p.task = None

    def _placement(self, pid):
        p = self.players[pid]
        if p.match_points >= 10 and p.placement is None:
            p.placement = min(set(range(1,len(self.players)+1)) - {x.placement for x in self.players.values()})
            if any(l['borrower'] == pid for l in self.loans.values()):
                p.match_points = 10
        self._exit_if_ready(pid)

    def _terminal(self):
        unplaced = [p for p in self.players.values() if p.placement is None and not p.forfeited]
        if len(unplaced) == 1:
            unplaced[0].placement = min(set(range(1,len(self.players)+1)) - {x.placement for x in self.players.values()})
            self._exit_if_ready(unplaced[0].id)
        if not self.active():
            self.phase = 'finished'
            self.economy_open = False
            self.current = None
            return True
        return False

    def end_turn(self, pid, now, missed=False):
        require(self.phase == 'regular' and self.current == pid, 'Wrong turn or phase')
        self.missed[pid] = self.missed[pid] + 1 if missed else 0
        if self.missed[pid] >= 3:
            self.forfeit(pid,now,'three consecutive missed regular turns')
        if self.mini:
            self._start_reactions([pid] if self.players[pid].active else [], now)
            return
        self.turn_list = [p for p in self.turn_list if p != pid and self.players[p].active]
        if self.turn_list:
            self._start_regular(self.turn_list[0], now)
        else:
            self.phase = 'action_resolution'
            self.economy_open = False
            groups = {'defence': 0, 'attack': 1, 'good': 2, 'chaos': 2}
            self.resolving = sorted(self.pending, key=lambda a: groups[a['category']])
            self.pending = []
            self._resolve(now)

    def _start_regular(self, pid, now):
        self.phase, self.current = 'regular', pid
        self.economy_open = True
        if self.defences[pid]['Secure Storage']:
            self.decks['action'].discard.extend(['Secure Storage'] * self.defences[pid].pop('Secure Storage'))
        self._income(self.players[pid])
        self.deadline = now + self.turn_seconds

    def _start_reactions(self, players, now):
        self.phase = 'reaction'
        self.reaction_list = players[:]
        self.economy_open = True
        self._next_reaction(now)

    def _next_reaction(self, now):
        self.reaction_list = [p for p in self.reaction_list if self.players[p].active]
        if not self.reaction_list:
            self.economy_open = False
            self.yields.clear()
            self.locked = []
            if not self.mini:
                self.mini_queue = [p for p in self.order for _ in range(self.extras[p]) if self.players[p].active]
                self.extras.clear()
            self._next_mini(now)
            return
        self.current = self.reaction_list[0]
        if self.players[self.current].task is None:
            self.players[self.current].task = self.decks['task'].draw(self.rng)
        self.opportunity = ReactionOpportunity(self.current)
        self.replaced = False
        self.deadline = now + self.turn_seconds

    def _next_mini(self, now):
        self.mini_queue = [p for p in self.mini_queue if self.players[p].active]
        if self.mini_queue:
            self.mini = True
            self._start_regular(self.mini_queue.pop(0), now)
        else:
            self._complete_round(now)

    def _complete_round(self, now):
        self.completed_rounds = self.round
        for loan in self.loans.values():
            if self.completed_rounds >= loan['due']:
                loan['penalty'] += 2
        for pid, defence in self.defences.items():
            for name, count in list(defence.items()):
                if name != 'Secure Storage':
                    self.decks['action'].discard.extend([name] * count)
                    del defence[name]
        if self.reverse_count % 2:
            self.order.reverse()
        self.reverse_count = 0
        self.round += 1
        self.mini = False
        for offer in self.offers.values():
            if offer.get('status','pending')=='pending':
                offer['status']='expired'
        if self._terminal():
            self.finished_at=now
            return
        # A forfeit result has undefined placements; stop when only one nonforfeit remains.
        if self.result_blocked and len(self.active()) <= 1:
            self.phase = 'blocked_forfeit_result'
            self.economy_open = False
            return
        self.turn_list = self.active()
        self._start_regular(self.turn_list[0], now)

    def create(self, pid, compound):
        self._own(pid, 'reaction')
        require(not self.replaced, 'Replacement task waits until next opportunity')
        require(self.players[pid].task is not None, 'Task supply unavailable')
        require(pid not in self.locked or self.mini, 'Lab Lockdown')
        before = self.players[pid].match_points
        points = self.opportunity.create(self, pid, compound)
        self.economy_open = False
        if points and not self.mini:
            self.players[pid].match_points = before + points * (2 ** self.yields.pop(pid, 0))
        self._placement(pid)

    def replace_task(self, pid):
        self._own(pid, 'reaction')
        require(not self.replaced and not self.opportunity.used, 'Opportunity already used')
        p = self.players[pid]
        require(p.task is not None, 'No task to replace')
        self._pay(pid, 20 + p.replacements * 5)
        self.decks['task'].discard.append(p.task)
        p.task = self.decks['task'].draw(self.rng)
        p.replacements += 1
        self.replaced = True

    def end_reaction(self, pid, now):
        require(self.phase == 'reaction' and self.current == pid, 'Wrong turn or phase')
        self.opportunity.finish(self)
        # Exited players must not receive a replacement task.
        if not self.players[pid].active and self.players[pid].task:
            self.decks['task'].discard.append(self.players[pid].task)
            self.players[pid].task = None
        self.reaction_list.pop(0)
        self._next_reaction(now)

    def play(self, pid, name, target=None):
        self._own(pid, 'regular')
        row = next((r for r in self.data['action'] if r['name'] == name), None)
        require(row is not None and self.players[pid].hand['action'][name] > 0, 'Action not owned')
        if row['category'] == 'attack' and name != 'Supply Shortage' or name in ('Market Swap', 'Unexpected Catalyst'):
            require(target in self.active() and target != pid, 'Choose another active target')
        self._pay(pid, 2)
        self._take(pid, ['action', name])
        self.sequence += 1
        self.pending.append(dict(id=str(self.sequence), actor=pid, name=name, category=row['category'], target=target))

    def _resolve(self, now):
        while not self.choice:
            if self.attack:
                self._advance_attack(now)
                if self.choice:
                    return
                continue
            if not self.resolving:
                self._start_reactions(self.active(), now)
                return
            action = self.resolving.pop(0)
            pid, name = action['actor'], action['name']
            if not self.players[pid].active:
                self.decks['action'].discard.append(name)
                continue
            if action['category'] == 'defence':
                self.defences[pid][name] += 1
                continue
            if action['category'] == 'attack':
                targets = [p for p in self.active() if p != pid] if name == 'Supply Shortage' else [action['target']]
                self.attack = dict(action=action, targets=targets, target=None, redirected=[], losses={}, selected=None, step='target')
                continue
            self.decks['action'].discard.append(name)
            self._effect(action, now)

    def _effect(self, a, now):
        pid, name = a['actor'], a['name']
        if name == 'Quick Experiment':
            self._draw(pid, 'reactant', 2)
        elif name == 'Extra Equipment':
            self._draw(pid, 'apparatus', 1)
        elif name == 'Double Yield':
            self.yields[pid] += 1
        elif name == 'Double Reaction':
            self.extras[pid] += 1
        elif name == 'Experiment Reversal':
            self.reverse_count += 1
        elif name == 'Formula Shuffle':
            players = self.active()
            outgoing = {p: self.rng.choice(self._cards(p)) for p in players if self._cards(p)}
            for p, card in outgoing.items():
                self._take(p, card)
            for p, card in outgoing.items():
                self._give(players[(players.index(p)+1) % len(players)], card)
        elif name == 'Research Breakthrough':
            drawn = [self.decks['reactant'].draw(self.rng) for _ in range(5)]
            cards = [['reactant', c] for c in drawn if c is not None]
            self._ask(pid, 'research', cards, min(2, len(cards)), now)
        elif name in ('Perfect Match', 'Lab Upgrade'):
            kind = 'reactant' if name == 'Perfect Match' else 'apparatus'
            cards = [[kind, c] for c in self.decks[kind].discard]
            if cards:
                self._ask(pid, 'recover', cards, 1, now)
        elif name == 'Lucky Reaction':
            self._ask(pid, 'lucky', ['reactant', 'apparatus', 'action'], 1, now)
        elif name == 'Chemical Discovery':
            self._draw(pid, 'reactant', 3)
            cards = self._cards(pid, ('reactant',))
            if cards:
                self._ask(pid, 'discard', cards, 1, now)
        elif name == 'Unexpected Catalyst':
            self._draw(pid, 'reactant', 2)
            if self.players[a['target']].active:
                self._draw(a['target'], 'reactant', 2)
        elif name == 'Mass Production':
            for p in self.active():
                self._draw(p, 'reactant', 3 if p == pid else 1)
        elif name in ('Chemical Spill', 'Equipment Recall'):
            kind = 'reactant' if name == 'Chemical Spill' else 'apparatus'
            # Recall is a player choice; process recipients through explicit choices.
            if name == 'Equipment Recall':
                self._recall(self.active(), now)
            else:
                for p in self.active():
                    cards = self._cards(p, (kind,))
                    if cards:
                        self._discard(p, self.rng.choice(cards))
        elif name == 'Market Swap':
            target = a['target']
            if self.players[target].active:
                cards = self._cards(pid)
                count = min(2, len(cards), len(self._cards(target)))
                if count:
                    self._ask(pid, 'swap', cards, count, now, {'target': target})
        else:
            raise RuleError('Unhandled action: ' + name)

    def _recall(self, players, now):
        while players:
            pid, *players = players
            cards = self._cards(pid, ('apparatus',))
            if cards:
                self._ask(pid, 'recall', cards, 1, now, {'remaining': players})
                return

    def _advance_attack(self, now):
        attack = self.attack
        a = attack['action']
        name, actor = a['name'], a['actor']
        if attack['target'] is None:
            if not attack['targets']:
                # Insurance considers total loss from all portions of this attack.
                for p, n in attack['losses'].items():
                    if p != actor and n >= 2 and self.defences[p]['Lab Insurance']:
                        self._consume(p, 'Lab Insurance')
                        self._draw(p, 'reactant', 2)
                self.decks['action'].discard.append(name)
                self.attack = None
                return
            attack['target'] = attack['targets'].pop(0)
            attack['step'] = 'defence'
        target = attack['target']
        if not self.players[target].active:
            attack['target'] = None
            return
        theft = name in ('Card Heist', 'Reactant Raid', 'Equipment Theft', 'Stolen Research')
        defence = self.defences[target]
        if attack['step'] == 'defence':
            if theft and defence['Secure Storage']:
                attack['target'] = None
                return
            if defence['Counter-Reaction'] and target not in attack['redirected']:
                self._ask(target, 'redirect', [p for p in self.active() if p != target] + [None], 1, now)
                return
            attack['step'] = 'goggles'
        if attack['step'] == 'goggles':
            if defence['Safety Goggles']:
                self._consume(target, 'Safety Goggles')
                attack['target'] = None
                return
            if name == 'Lab Lockdown':
                if target not in self.locked:
                    self.locked.append(target)
                attack['target'] = None
                return
            kinds = ('reactant',) if name in ('Reactant Raid', 'Contamination!', 'Supply Shortage') else ('apparatus',) if name == 'Equipment Theft' else ('action',) if name == 'Stolen Research' else ('reactant', 'apparatus', 'action')
            cards = self._cards(target, kinds)
            count = min(len(cards), 2 if name in ('Card Heist', 'Contamination!') else 1)
            if count == 0:
                attack['target'] = None
                return
            if name in ('Reactant Raid', 'Equipment Theft', 'Contamination!', 'Supply Shortage'):
                chooser = actor if name in ('Reactant Raid', 'Equipment Theft') else target
                self._ask(chooser, 'attack_select', cards, count, now)
                return
            attack['selected'] = self.rng.sample(cards, count)
            attack['step'] = 'backup'
        if attack['step'] == 'backup':
            if target != actor and defence['Emergency Backup'] and attack['selected']:
                self._ask(target, 'backup', attack['selected'], 1, now)
                return
            attack['step'] = 'apply'
        if attack['step'] == 'apply':
            cards = attack['selected']
            for card in cards:
                self._take(target, card)
                if theft:
                    self._give(actor, card)
                else:
                    self.decks[card[0]].discard.append(card[1])
            attack['losses'][target] = attack['losses'].get(target, 0) + len(cards)
            attack['target'] = None

    def _consume(self, pid, name):
        self.defences[pid][name] -= 1
        self.decks['action'].discard.append(name)

    def choose(self, pid, selected, now):
        c = self.choice
        require(c is not None and c['player'] == pid, 'Not your choice')
        require(isinstance(selected, list) and len(selected) == c['count'], 'Wrong selection count')
        remaining = deepcopy(c['options'])
        for value in selected:
            require(value in remaining, 'Invalid choice')
            remaining.remove(value)
        mode = c['mode']
        if mode == 'redirect':
            attack = self.attack
            if selected[0] is None:
                attack['step'] = 'goggles'
            else:
                self._consume(pid, 'Counter-Reaction')
                attack['redirected'].append(pid)
                attack['target'] = selected[0]
                attack['step'] = 'defence'
        elif mode == 'attack_select':
            self.attack['selected'] = deepcopy(selected)
            self.attack['step'] = 'backup'
        elif mode == 'backup':
            self._consume(pid, 'Emergency Backup')
            self.attack['selected'].remove(selected[0])
            self.attack['step'] = 'apply'
        elif mode == 'research':
            for card in selected:
                self._give(pid, card)
            for card in remaining:
                self.decks[card[0]].discard.append(card[1])
        elif mode == 'recover':
            card = selected[0]
            self.decks[card[0]].discard.remove(card[1])
            self._give(pid, card)
        elif mode in ('discard', 'recall'):
            for card in selected:
                self._discard(pid, card)
        elif mode == 'lucky':
            self._draw(pid, selected[0], 1)
        elif mode == 'swap':
            target = c['context']['target']
            taken = self.rng.sample(self._cards(target), len(selected))
            for card in selected:
                self._take(pid, card)
            for card in taken:
                self._take(target, card)
            for card in selected:
                self._give(target, card)
            for card in taken:
                self._give(pid, card)
        self.choice = None
        if mode == 'recall':
            self._recall(c['context']['remaining'], now)
        self._resolve(now)

    def disconnect(self, pid, now):
        require(pid in self.players, 'Unknown player')
        self.disconnected.setdefault(pid, now)

    def reconnect(self, pid, now):
        require(pid in self.players, 'Unknown player')
        started = self.disconnected.get(pid)
        require(not self.players[pid].forfeited, 'Player forfeited')
        self.disconnected.pop(pid, None)
        if started is not None and now <= started+90 and self.current == pid and self.phase == 'regular':
            self.deadline = max(self.deadline, now + self.turn_seconds)

    def forfeit(self, pid, now, reason='voluntary forfeit'):
        p=self.players[pid]
        require(p.active, 'Inactive player')
        # Approved settlement priority: oldest server-issued loan sequence first.
        claims=sorted(((key,loan) for key,loan in self.loans.items() if loan['borrower']==pid),key=lambda pair:int(pair[0]))
        p.pesos+=p.savings
        p.savings=0
        for key,l in claims:
            returned=[]
            default_cards=[]
            for card in l['cards']:
                if self.players[pid].hand[card[0]][card[1]]:
                    returned.append(card)
                    self._transfer(pid,l['lender'],{'cards':[card]})
                else:
                    default_cards.append(card)
            amount=min(p.pesos,l['pesos']+l['penalty'])
            self._transfer(pid,l['lender'],{'pesos':amount})
            self.loan_history.append(dict(id=key,**deepcopy(l),status='defaulted' if default_cards or amount<l['pesos']+l['penalty'] else 'settled',
                                         default_cards=default_cards,default_pesos=l['pesos']+l['penalty']-amount))
            del self.loans[key]
        if p.placement is None:
            p.placement=max(set(range(1,len(self.players)+1)) - {x.placement for x in self.players.values()})
        p.forfeited=True
        self.forfeits[pid]={'reason':reason,'at':now,'sequence':len(self.forfeits)+1}
        self._exit_if_ready(pid)
        if self.choice and self.choice['player']==pid:
            if self.choice['mode']=='research':
                self.decks['reactant'].discard.extend(card[1] for card in self.choice['options'])
            self.choice=None
            self._resolve(now)
        self.event('player.forfeited',now,player=pid,reason=reason)

    def tick(self, now):
        for key,offer in self.offers.items():
            if offer.get('status','pending')=='pending' and now>=offer['deadline']:
                offer['status']='expired'
                self.event('proposal.expired',now,offer=key)
        if self.choice and now >= self.choice['deadline']:
            choice=self.choice
            options=sorted(choice['options'], key=lambda x:json_sort(x))
            selected=[None] if choice['mode']=='redirect' else options[:choice['count']]
            require(len(selected)==choice['count'],'Blocked rule: no legal automatic selection')
            self.event('choice.automatic',now,player=choice['player'],mode=choice['mode'])
            self.choose(choice['player'],selected,now)
        elif self.phase == 'regular' and now >= self.deadline:
            started = self.disconnected.get(self.current)
            if started is not None and now < started + 90:
                return
            self.end_turn(self.current, now, missed=True)
        elif self.phase == 'reaction' and now >= self.deadline:
            self.end_reaction(self.current, now)

    def command(self, pid, name, args, now):
        require(pid in self.players, 'Not a match participant')
        handlers = {
            'buy': lambda: self.buy(pid, args['kind']),
            'bank': lambda: self.bank(pid, args['amount'], args.get('withdraw', False)),
            'offer': lambda: self.offer(pid, args['target'], args['give'], args.get('receive', {}), now, args.get('loan_rounds')),
            'accept': lambda: self.accept(pid, args['offer'], now),
            'decline': lambda: self.decline(pid,args['offer']),
            'substitute': lambda: self.substitute(pid, args['loan'], args['pesos']),
            'repay': lambda: self.repay(pid, args['loan'], args.get('substitute', False)),
            'play': lambda: self.play(pid, args['card'], args.get('target')),
            'choose': lambda: self.choose(pid, args['selected'], now),
            'create': lambda: self.create(pid, args['compound']),
            'scan': lambda: self.scan(pid,args['task_id'],args['card_ids']),
            'forfeit': lambda: self.forfeit(pid,now),
            'replace': lambda: self.replace_task(pid),
            'end_turn': lambda: self.end_turn(pid, now),
            'end_reaction': lambda: self.end_reaction(pid, now),
        }
        require(name in handlers, 'Unknown command')
        # All authoritative entry points use rollback, including RNG and decisions.
        state = self.to_state()
        try:
            handlers[name]()
            self._sync_instances()
            self.event('command.accepted',now,player=pid,command=name)
            if self.phase == 'regular' and self.current and not self.players[self.current].active:
                self.end_turn(self.current, now)
            elif name=='forfeit' and self.phase == 'reaction' and self.current and not self.players[self.current].active:
                self.end_reaction(self.current,now)
        except (RuleError, KeyError, TypeError, ValueError, IndexError) as exc:
            self.__dict__ = self.from_state(state).__dict__
            raise RuleError(str(exc)) from exc

    def snapshot(self, viewer):
        self._sync_instances()
        result = super().snapshot(viewer)
        result.update(round=self.round, completed_rounds=self.completed_rounds, mini=self.mini,
                      economy_open=self.economy_open, deadline=self.deadline,
                      choice=deepcopy(self.choice) if self.choice and self.choice['player'] == viewer else None,
                      waiting_for=self.choice['player'] if self.choice else None,
                      placements={p: x.placement for p, x in self.players.items()},
                      loans=deepcopy(self.loans), escrow=deepcopy(self.escrow.get(viewer)),
                      offers={k: deepcopy(v) for k, v in self.offers.items() if viewer in (v['sender'], v['target'])},
                      result_blocked=self.result_blocked)
        result.update(instances=deepcopy(self.card_ids[viewer]),task_id=self.task_ids[viewer]['id'],
                      started_at=getattr(self,'started_at',None),finished_at=getattr(self,'finished_at',None),
                      recipe=next((deepcopy(r) for r in self.data['task'] if r['name']==self.players[viewer].task),None),
                      history=self.history[-100:],loan_history=deepcopy(self.loan_history),forfeits=deepcopy(self.forfeits),
                      pending_actions=[{k:a[k] for k in ('actor','name','target')} for a in self.pending+self.resolving],
                      incoming_attack=deepcopy(self.attack['action']) if self.attack else None,
                      ranking_awards={p:0 if x.forfeited else {1:30,2:15,3:5,4:0}.get(x.placement,0) for p,x in self.players.items()} if self.phase=='finished' else {})
        legal=[]
        if self.players[viewer].active:
            legal.append('forfeit')
            if self.economy_open and self.phase in ('regular','reaction'):
                legal.extend(['bank','repay','offer','accept','decline'])
            if self.phase=='regular' and self.current==viewer:
                legal.extend(['buy','play','end_turn'])
            if self.phase=='reaction' and self.current==viewer:
                legal.append('end_reaction')
                if not self.replaced and not self.opportunity.used:
                    legal.extend(['scan','replace'])
        if self.choice and self.choice['player']==viewer:
            legal.append('choose')
        if self.phase=='reaction' and self.current==viewer and 'end_reaction' not in legal:
            legal.append('end_reaction')
        result['legal_commands']=legal
        return result

    def to_state(self):
        state = {k: deepcopy(v) for k, v in self.__dict__.items() if k not in ('rng', 'data', 'players', 'decks', 'opportunity')}
        state.update(schema=2, rng=self.rng.getstate(), players={p: {**deepcopy(v.__dict__), 'hand': {k: dict(c) for k, c in v.hand.items()}} for p, v in self.players.items()},
                     decks={k: asdict(v) for k, v in self.decks.items()},
                     opportunity=asdict(self.opportunity) if self.opportunity else None)
        return state

    @classmethod
    def from_state(cls, state):
        import random
        state = deepcopy(state)
        require(state.pop('schema') == 2, 'Unsupported state version')
        match = cls.__new__(cls)
        match.__dict__.update(state)
        for key,default in dict(history=[],loan_history=[],forfeits={},card_ids={p:{} for p in state['players']},instance_sequence=0,
                                task_ids={p:{'name':x['task'],'id':f'task-{p}-0'} for p,x in state['players'].items()}).items():
            match.__dict__.setdefault(key,default)
        match.data = catalog()
        match.players = {p: Player(**v) for p, v in state['players'].items()}
        for p in match.players.values():
            p.hand = {k: Counter(v) for k, v in p.hand.items()}
        match.decks = {k: Deck(**v) for k, v in state['decks'].items()}
        match.opportunity = ReactionOpportunity(**state['opportunity']) if state['opportunity'] else None
        match.rng = random.Random()
        def tuples(value):
            return tuple(map(tuples, value)) if isinstance(value, (list, tuple)) else value
        match.rng.setstate(tuples(state['rng']))
        match.extras = Counter(state['extras'])
        match.yields = Counter(state['yields'])
        match.defences = {p: Counter(v) for p, v in state['defences'].items()}
        return match


def json_sort(value):
    import json
    return json.dumps(value,sort_keys=True)

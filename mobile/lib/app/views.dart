// ignore_for_file: deprecated_member_use
import 'dart:convert';

import 'package:flutter/material.dart';

import '../core/models.dart';
import 'controller.dart';

class AppView extends StatelessWidget {
  final AppController c;
  const AppView(this.c, {super.key});
  @override
  Widget build(BuildContext context) => AnimatedBuilder(
    animation: c,
    builder: (context, _) => Scaffold(
      appBar: AppBar(
        title: Text(
          c.profile == null ? 'CHEMa’t' : 'CHEMa’t — ${c.profile!.username}',
        ),
        actions: [
          if (c.profile != null)
            IconButton(
              key: const ValueKey('profile'),
              tooltip: 'Profile',
              icon: const Icon(Icons.person),
              onPressed: () => showDialog<void>(
                context: context,
                builder: (_) => ProfileDialog(c),
              ),
            ),
        ],
      ),
      body: Column(
        children: [
          if (c.busy) const LinearProgressIndicator(),
          if (c.error != null)
            MaterialBanner(
              content: Text(c.error!, key: const ValueKey('error')),
              actions: [
                TextButton(
                  onPressed: () {
                    c.error = null;
                    c.notify();
                  },
                  child: const Text('Dismiss'),
                ),
              ],
            ),
          if (c.notice != null) Text(c.notice!),
          if (!c.initialized)
            const Text('Starting…')
          else if (c.profile != null)
            Text(c.connection, key: const ValueKey('connection')),
          Expanded(
            child: !c.initialized
                ? const SizedBox()
                : c.profile == null
                ? RegisterView(c)
                : c.game != null
                ? GameView(c)
                : c.lobby != null
                ? LobbyView(c)
                : HomeView(c),
          ),
        ],
      ),
    ),
  );
}

class RegisterView extends StatefulWidget {
  final AppController c;
  const RegisterView(this.c, {super.key});
  @override
  State<RegisterView> createState() => _RegisterState();
}

class _RegisterState extends State<RegisterView> {
  final username = TextEditingController();
  late final endpoint = TextEditingController(text: widget.c.api.endpoint);
  @override
  void dispose() {
    username.dispose();
    endpoint.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) => ListView(
    padding: const EdgeInsets.all(16),
    children: [
      const Text('Create a local profile. No email or password is required.'),
      TextField(
        key: const ValueKey('username'),
        controller: username,
        maxLength: 32,
        decoration: const InputDecoration(labelText: 'Username'),
      ),
      TextButton(
        onPressed: () => widget.c.availability(username.text),
        child: const Text('Check username availability'),
      ),
      TextField(
        key: const ValueKey('endpoint'),
        controller: endpoint,
        decoration: const InputDecoration(labelText: 'Backend URL'),
      ),
      FilledButton(
        key: const ValueKey('register'),
        onPressed: widget.c.busy
            ? null
            : () => widget.c.register(username.text, endpoint.text),
        child: const Text('Create profile'),
      ),
      const Text(
        'Device credentials are stored securely. Removing them can permanently lose access. No recovery service is available.',
      ),
    ],
  );
}

class HomeView extends StatefulWidget {
  final AppController c;
  const HomeView(this.c, {super.key});
  @override
  State<HomeView> createState() => _HomeState();
}

class _HomeState extends State<HomeView> {
  final code = TextEditingController();
  @override
  void dispose() {
    code.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) => ListView(
    padding: const EdgeInsets.all(16),
    children: [
      Text('Player ID: ${widget.c.id}', key: const ValueKey('player-id')),
      FilledButton(
        key: const ValueKey('create-lobby'),
        onPressed: widget.c.busy ? null : () => widget.c.createLobby(),
        child: const Text('Create private lobby'),
      ),
      TextField(
        key: const ValueKey('invite-code'),
        controller: code,
        decoration: const InputDecoration(labelText: 'Invite code'),
      ),
      OutlinedButton(
        key: const ValueKey('join-lobby'),
        onPressed: widget.c.busy ? null : () => widget.c.join(code.text),
        child: const Text('Join lobby'),
      ),
      OutlinedButton(
        onPressed: () => widget.c.createLobby(public: true),
        child: const Text('Public matchmaking'),
      ),
      OutlinedButton(
        onPressed: () {
          widget.c.social();
          Navigator.push(
            context,
            MaterialPageRoute<void>(builder: (_) => SocialView(widget.c)),
          );
        },
        child: const Text('Friends and monthly rankings'),
      ),
    ],
  );
}

class ProfileDialog extends StatefulWidget {
  final AppController c;
  const ProfileDialog(this.c, {super.key});
  @override
  State<ProfileDialog> createState() => _ProfileState();
}

class _ProfileState extends State<ProfileDialog> {
  late final name = TextEditingController(text: widget.c.profile!.username);
  @override
  void dispose() {
    name.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) => AlertDialog(
    title: const Text('Local profile'),
    content: TextField(
      controller: name,
      decoration: const InputDecoration(labelText: 'Username'),
    ),
    actions: [
      TextButton(
        onPressed: () {
          widget.c.rename(name.text);
          Navigator.pop(context);
        },
        child: const Text('Save username'),
      ),
      TextButton(
        key: const ValueKey('reset-profile'),
        onPressed: () async {
          final confirmed = await showDialog<bool>(
            context: context,
            builder: (context) => AlertDialog(
              title: const Text('Delete local profile?'),
              content: const Text(
                'This removes your local profile and secure credentials. Account access may be permanently lost. No recovery method exists.',
              ),
              actions: [
                TextButton(
                  onPressed: () => Navigator.pop(context, false),
                  child: const Text('Cancel'),
                ),
                TextButton(
                  key: const ValueKey('confirm-reset'),
                  onPressed: () => Navigator.pop(context, true),
                  child: const Text('Delete local data'),
                ),
              ],
            ),
          );
          if (confirmed == true) {
            await widget.c.reset();
            if (context.mounted) Navigator.pop(context);
          }
        },
        child: const Text('Reset local profile'),
      ),
      TextButton(
        onPressed: () => Navigator.pop(context),
        child: const Text('Close'),
      ),
    ],
  );
}

class LobbyView extends StatelessWidget {
  final AppController c;
  const LobbyView(this.c, {super.key});
  @override
  Widget build(BuildContext context) {
    final lobby = c.lobby!;
    final ready = List<String>.from(lobby['ready']);
    return ListView(
      padding: const EdgeInsets.all(16),
      children: [
        Text(lobby['code'], key: const ValueKey('lobby-code')),
        Text('Lobby: ${lobby['status']} | 2–4 players'),
        for (final pid in lobby['members'])
          ListTile(
            title: Text(lobby['usernames'][pid] ?? pid),
            subtitle: Text(
              '${pid == lobby['owner'] ? 'Host' : 'Player'} — ${ready.contains(pid) ? 'Ready' : 'Not ready'}',
            ),
          ),
        FilledButton(
          key: const ValueKey('ready'),
          onPressed: c.busy
              ? null
              : () => c.lobbyAction(ready.contains(c.id) ? 'unready' : 'ready'),
          child: Text(ready.contains(c.id) ? 'Unready' : 'Ready'),
        ),
        if (c.id == lobby['owner'])
          FilledButton(
            key: const ValueKey('start-match'),
            onPressed: c.busy ? null : () => c.lobbyAction('start'),
            child: const Text('Start match'),
          ),
        OutlinedButton(
          onPressed: () => c.lobbyAction('leave'),
          child: const Text('Leave lobby'),
        ),
        if (c.id == lobby['owner'])
          TextButton(
            onPressed: () => c.lobbyAction('cancel'),
            child: const Text('Cancel lobby'),
          ),
      ],
    );
  }
}

class GameView extends StatelessWidget {
  final AppController c;
  const GameView(this.c, {super.key});
  @override
  Widget build(BuildContext context) {
    final g = c.game!;
    final s = g.state;
    final p = g.player(c.id);
    final recipe = g.recipe;
    final legal = g.legal;
    Widget button(String name, String label, [Json args = const {}]) =>
        FilledButton(
          key: ValueKey(name),
          onPressed: c.busy || !legal.contains(name)
              ? null
              : () => c.command(name, args),
          child: Text(label),
        );
    return ListView(
      key: const ValueKey('game-scroll'),
      padding: const EdgeInsets.all(16),
      children: [
        Text('Match: ${c.profile!.match}', key: const ValueKey('match-id')),
        Text(
          'Phase: ${g.phase} | Round: ${s['round']} | ${s['mini'] ? 'Double Reaction mini-round' : 'Shared round'}',
          key: const ValueKey('phase'),
        ),
        Text(
          'Active player: ${g.current == c.id ? 'You' : g.current ?? 'None'}',
          key: const ValueKey('active-player'),
        ),
        Text(
          'Pesos: ${p['pesos']} | Match Points: ${p['match_points']} | Savings: ${p['savings']}',
          key: const ValueKey('balances'),
        ),
        Text(
          'Remaining: ${((s['deadline'] as num) - DateTime.now().millisecondsSinceEpoch / 1000).ceil().clamp(0, 99999)} seconds',
        ),
        for (final entry in (s['players'] as Map).entries)
          if (entry.key != c.id)
            Text(
              'Opponent ${entry.key}: ${entry.value['match_points']} Match Points, ${entry.value['pesos']} pesos',
            ),
        if (g.finished) ...[
          const Text('Match complete', key: ValueKey('results')),
          if (s['finished_at'] != null && s['started_at'] != null)
            Text(
              'Duration: ${((s['finished_at'] as num) - (s['started_at'] as num)).round()} seconds',
            ),
          for (final entry in (s['placements'] as Map).entries)
            Text(
              '${entry.key == c.id ? 'You' : entry.key}: place ${entry.value}, Ranking Points ${s['ranking_awards'][entry.key]}${s['forfeits'][entry.key] != null ? ' (forfeit)' : ''}',
            ),
          OutlinedButton(
            onPressed: c.leaveResults,
            child: const Text('Return home'),
          ),
        ] else ...[
          Text(
            'Task: ${p['task'] ?? 'Waiting for Task supply'}',
            key: const ValueKey('task'),
          ),
          if (recipe != null) ...[
            Text(
              'Reactants: ${(recipe['reactants'] as List).join(' + ')}',
              key: const ValueKey('required-reactants'),
            ),
            Text(
              'Apparatus: ${(recipe['apparatus'] as List).join(' + ')}',
              key: const ValueKey('required-apparatus'),
            ),
            Text(
              '${recipe['difficulty']} | ${recipe['points']} Match Points | Fee: ${recipe['fee']} pesos',
            ),
          ],
          ExpansionTile(
            title: Text('Hand (${g.instances.length} cards)'),
            children: [
              for (final entry in g.instances.entries)
                ListTile(
                  key: ValueKey('hand-${entry.key}'),
                  title: Text('${entry.value[0]}: ${entry.value[1]}'),
                  trailing: entry.value[0] == 'action'
                      ? TextButton(
                          onPressed: !legal.contains('play') || c.busy
                              ? null
                              : () => playAction(context, entry.value[1]),
                          child: const Text('Play'),
                        )
                      : null,
                  onTap: () => showDialog<void>(
                    context: context,
                    builder: (_) => AlertDialog(
                      title: Text(entry.value[1]),
                      content: Text(description(entry.value[1])),
                      actions: [
                        TextButton(
                          onPressed: () => Navigator.pop(context),
                          child: const Text('Close'),
                        ),
                      ],
                    ),
                  ),
                ),
            ],
          ),
          Wrap(
            spacing: 8,
            children: [
              for (final kind in ['reactant', 'apparatus', 'action'])
                OutlinedButton(
                  key: ValueKey('buy-$kind'),
                  onPressed: !legal.contains('buy') || c.busy
                      ? null
                      : () => c.command('buy', {'kind': kind}),
                  child: Text(
                    'Buy $kind (${kind == 'action' ? 2 : 1} peso${kind == 'action' ? 's' : ''})',
                  ),
                ),
            ],
          ),
          if (g.choice != null) ChoicePanel(c),
          if (s['incoming_attack'] != null)
            Text(
              'Incoming action: ${s['incoming_attack']['name']} from ${s['incoming_attack']['actor']}',
            ),
          if ((s['pending_actions'] as List).isNotEmpty)
            Text(
              'Queued actions: ${(s['pending_actions'] as List).map((a) => a['name']).join(', ')}',
            ),
          OutlinedButton(
            key: const ValueKey('scanner'),
            onPressed: !legal.contains('scan') || c.busy
                ? null
                : () => showDialog<void>(
                    context: context,
                    builder: (_) => ScannerDialog(c),
                  ),
            child: const Text('Scan compound cards'),
          ),
          button(
            'replace',
            'Replace Task (${20 + (p['replacements'] as int) * 5} pesos)',
          ),
          Wrap(
            spacing: 8,
            children: [
              for (final withdraw in [false, true])
                OutlinedButton(
                  onPressed: !legal.contains('bank') || c.busy
                      ? null
                      : () => amount(
                          context,
                          withdraw
                              ? 'Withdraw savings'
                              : 'Deposit (1 peso fee)',
                          (n) => c.command('bank', {
                            'amount': n,
                            'withdraw': withdraw,
                          }),
                        ),
                  child: Text(withdraw ? 'Withdraw' : 'Deposit'),
                ),
            ],
          ),
          OutlinedButton(
            key: const ValueKey('propose-trade'),
            onPressed: !legal.contains('offer') || c.busy
                ? null
                : () => showDialog<void>(
                    context: context,
                    builder: (_) => OfferDialog(c),
                  ),
            child: const Text('Trade, gift or loan'),
          ),
          for (final entry in (s['offers'] as Map).entries)
            ListTile(
              title: Text('Proposal ${entry.key}: ${entry.value['status']}'),
              subtitle: Text(
                '${entry.value['sender']} → ${entry.value['target']}\nGive: ${entry.value['give']}\nRequest: ${entry.value['receive']}\nExpires: ${DateTime.fromMillisecondsSinceEpoch((entry.value['deadline'] * 1000).round()).toLocal()}',
              ),
              trailing:
                  entry.value['target'] == c.id &&
                      entry.value['status'] == 'pending'
                  ? Wrap(
                      children: [
                        TextButton(
                          key: ValueKey('accept-${entry.key}'),
                          onPressed: c.busy
                              ? null
                              : () => c.command('accept', {'offer': entry.key}),
                          child: const Text('Accept'),
                        ),
                        TextButton(
                          onPressed: () =>
                              c.command('decline', {'offer': entry.key}),
                          child: const Text('Decline'),
                        ),
                      ],
                    )
                  : null,
            ),
          for (final entry in (s['loans'] as Map).entries)
            ListTile(
              title: Text('Loan ${entry.key}: due round ${entry.value['due']}'),
              subtitle: Text(
                '${entry.value['pesos']} pesos + ${entry.value['penalty']} penalty; cards ${entry.value['cards']}',
              ),
              trailing: entry.value['borrower'] == c.id
                  ? Wrap(
                      children: [
                        TextButton(
                          onPressed: !legal.contains('repay')
                              ? null
                              : () => c.command('repay', {'loan': entry.key}),
                          child: const Text('Repay'),
                        ),
                        if (entry.value['substitution'] != null)
                          TextButton(
                            onPressed: () => c.command('repay', {
                              'loan': entry.key,
                              'substitute': true,
                            }),
                            child: Text(
                              'Pay substitution (${entry.value['substitution']})',
                            ),
                          ),
                      ],
                    )
                  : entry.value['lender'] == c.id
                  ? TextButton(
                      onPressed: () => amount(
                        context,
                        'Approve peso substitution',
                        (n) => c.command('substitute', {
                          'loan': entry.key,
                          'pesos': n,
                        }),
                      ),
                      child: const Text('Approve substitution'),
                    )
                  : null,
            ),
          Text('Settled loans: ${s['loan_history']}'),
          button('end_turn', 'End regular turn'),
          button('end_reaction', 'Finish Reaction opportunity'),
          TextButton(
            onPressed: !legal.contains('forfeit')
                ? null
                : () async {
                    final yes = await showDialog<bool>(
                      context: context,
                      builder: (context) => AlertDialog(
                        title: const Text('Forfeit match?'),
                        content: const Text(
                          'You receive the lowest available placement and zero Ranking Points. Debts will be settled or recorded as defaults.',
                        ),
                        actions: [
                          TextButton(
                            onPressed: () => Navigator.pop(context, false),
                            child: const Text('Cancel'),
                          ),
                          TextButton(
                            onPressed: () => Navigator.pop(context, true),
                            child: const Text('Forfeit'),
                          ),
                        ],
                      ),
                    );
                    if (yes == true) c.command('forfeit');
                  },
            child: const Text('Forfeit match'),
          ),
        ],
        Text(
          'Recent activity: ${(s['history'] as List).reversed.take(8).map((e) => e['event']).join(', ')}',
        ),
        TextButton(
          onPressed: () => c.run(c.refresh),
          child: const Text('Refresh state'),
        ),
      ],
    );
  }

  String description(String name) {
    for (final card in (c.catalog['action'] ?? []) as List) {
      if (card['name'] == name) {
        return card['description'] ??
            '${card['category']} Action Card. Buy: 2 pesos; play: 2 pesos. Effects resolve on the server.';
      }
    }
    return 'Game card consumed when required by your active Task. Recipes are card requirements, not laboratory instructions.';
  }

  Future<void> playAction(BuildContext context, String name) async {
    final action = (c.catalog['action'] as List).firstWhere(
      (r) => r['name'] == name,
    );
    String? target;
    if (action['requires_target'] == true) {
      target = await showDialog<String>(
        context: context,
        builder: (context) => SimpleDialog(
          title: const Text('Select target'),
          children: [
            for (final p in (c.game!.state['players'] as Map).entries)
              if (p.key != c.id && p.value['active'])
                SimpleDialogOption(
                  onPressed: () => Navigator.pop(context, p.key),
                  child: Text(p.key),
                ),
          ],
        ),
      );
      if (target == null) return;
    }
    if (!context.mounted) return;
    final yes = await showDialog<bool>(
      context: context,
      builder: (context) => AlertDialog(
        title: Text('Play $name?'),
        content: Text(
          '${description(name)}\nPlaying costs 2 pesos. Effects are queued; failed effects are not refunded.',
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(context, false),
            child: const Text('Cancel'),
          ),
          FilledButton(
            onPressed: () => Navigator.pop(context, true),
            child: const Text('Confirm'),
          ),
        ],
      ),
    );
    if (yes == true) c.command('play', {'card': name, 'target': target});
  }
}

Future<void> amount(
  BuildContext context,
  String title,
  Future<void> Function(int) submit,
) async {
  final input = TextEditingController();
  final n = await showDialog<int>(
    context: context,
    builder: (context) => AlertDialog(
      title: Text(title),
      content: TextField(
        controller: input,
        keyboardType: TextInputType.number,
        decoration: const InputDecoration(labelText: 'Pesos'),
      ),
      actions: [
        TextButton(
          onPressed: () => Navigator.pop(context),
          child: const Text('Cancel'),
        ),
        FilledButton(
          onPressed: () => Navigator.pop(context, int.tryParse(input.text)),
          child: const Text('Confirm'),
        ),
      ],
    ),
  );
  if (n != null) await submit(n);
  input.dispose();
}

class ScannerDialog extends StatefulWidget {
  final AppController c;
  const ScannerDialog(this.c, {super.key});
  @override
  State<ScannerDialog> createState() => _ScannerState();
}

class _ScannerState extends State<ScannerDialog> {
  final selected = <String>{};
  @override
  Widget build(BuildContext context) => AlertDialog(
    title: const Text('Select compound cards'),
    content: SizedBox(
      width: 420,
      child: SingleChildScrollView(
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            Text('Task: ${widget.c.game!.recipe?['name']}'),
            for (final entry in widget.c.game!.instances.entries)
              if (entry.value[0] != 'action')
                CheckboxListTile(
                  key: ValueKey('scan-${entry.key}'),
                  title: Text('${entry.value[0]}: ${entry.value[1]}'),
                  value: selected.contains(entry.key),
                  onChanged: (value) => setState(
                    () => value == true
                        ? selected.add(entry.key)
                        : selected.remove(entry.key),
                  ),
                ),
          ],
        ),
      ),
    ),
    actions: [
      TextButton(
        onPressed: () => Navigator.pop(context),
        child: const Text('Cancel'),
      ),
      FilledButton(
        key: const ValueKey('submit-scan'),
        onPressed: () {
          final task = widget.c.game!.state['task_id'];
          widget.c.command('scan', {
            'task_id': task,
            'card_ids': selected.toList(),
          });
          Navigator.pop(context);
        },
        child: const Text('Validate and create'),
      ),
    ],
  );
}

class ChoicePanel extends StatefulWidget {
  final AppController c;
  const ChoicePanel(this.c, {super.key});
  @override
  State<ChoicePanel> createState() => _ChoiceState();
}

class _ChoiceState extends State<ChoicePanel> {
  final selected = <int>{};
  String previous = '';
  @override
  Widget build(BuildContext context) {
    final choice = widget.c.game!.choice!;
    final identity = jsonEncode(choice);
    if (identity != previous) {
      selected.clear();
      previous = identity;
    }
    final options = choice['options'] as List;
    return Card(
      child: Column(
        children: [
          Text('Response: ${choice['mode']} — choose ${choice['count']}'),
          for (var i = 0; i < options.length; i++)
            CheckboxListTile(
              title: Text(
                options[i] == null ? 'Decline redirect' : options[i].toString(),
              ),
              value: selected.contains(i),
              onChanged: (v) => setState(
                () => v == true ? selected.add(i) : selected.remove(i),
              ),
            ),
          FilledButton(
            onPressed: widget.c.busy || selected.length != choice['count']
                ? null
                : () => widget.c.command('choose', {
                    'selected': selected.map((i) => options[i]).toList(),
                  }),
            child: const Text('Confirm response'),
          ),
        ],
      ),
    );
  }
}

class OfferDialog extends StatefulWidget {
  final AppController c;
  const OfferDialog(this.c, {super.key});
  @override
  State<OfferDialog> createState() => _OfferState();
}

class _OfferState extends State<OfferDialog> {
  String? target;
  final give = TextEditingController(text: '0'),
      receive = TextEditingController(text: '0'),
      rounds = TextEditingController(text: '2');
  final selected = <String>{};
  final requested = <dynamic>[];
  bool loan = false;
  String? requestCard;
  @override
  void dispose() {
    give.dispose();
    receive.dispose();
    rounds.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final c = widget.c;
    final choices = <String, List<String>>{
      for (final kind in ['reactant', 'apparatus', 'action'])
        for (final card in c.catalog[kind])
          '$kind: ${card['name']}': [kind, card['name']],
    };
    return AlertDialog(
      title: const Text('Trade, gift or loan'),
      content: SizedBox(
        width: 440,
        child: SingleChildScrollView(
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              DropdownButtonFormField<String>(
                key: const ValueKey('offer-target'),
                isExpanded: true,
                initialValue: target,
                items: [
                  for (final p in (c.game!.state['players'] as Map).entries)
                    if (p.key != c.id && p.value['active'])
                      DropdownMenuItem(
                        value: p.key,
                        child: Text(p.key, overflow: TextOverflow.ellipsis),
                      ),
                ],
                onChanged: (v) => setState(() => target = v),
                decoration: const InputDecoration(labelText: 'Other player'),
              ),
              SwitchListTile(
                title: const Text('Offer as loan'),
                value: loan,
                onChanged: (v) => setState(() => loan = v),
              ),
              TextField(
                key: const ValueKey('give-pesos'),
                controller: give,
                keyboardType: TextInputType.number,
                decoration: const InputDecoration(labelText: 'Offer pesos'),
              ),
              for (final entry in c.game!.instances.entries)
                CheckboxListTile(
                  key: ValueKey('offer-${entry.key}'),
                  title: Text('${entry.value[0]}: ${entry.value[1]}'),
                  value: selected.contains(entry.key),
                  onChanged: (v) => setState(
                    () => v == true
                        ? selected.add(entry.key)
                        : selected.remove(entry.key),
                  ),
                ),
              if (loan)
                TextField(
                  controller: rounds,
                  keyboardType: TextInputType.number,
                  decoration: const InputDecoration(
                    labelText: 'Repay within shared rounds',
                  ),
                )
              else ...[
                TextField(
                  controller: receive,
                  keyboardType: TextInputType.number,
                  decoration: const InputDecoration(
                    labelText: 'Request pesos (0 for gift)',
                  ),
                ),
                DropdownButtonFormField<String>(
                  isExpanded: true,
                  items: [
                    for (final key in choices.keys)
                      DropdownMenuItem(value: key, child: Text(key)),
                  ],
                  onChanged: (v) => requestCard = v,
                  decoration: const InputDecoration(
                    labelText: 'Request card type',
                  ),
                ),
                TextButton(
                  onPressed: () => setState(() {
                    if (requestCard != null) {
                      requested.add(choices[requestCard]);
                    }
                  }),
                  child: const Text('Add requested card'),
                ),
                Text('Requested cards: $requested'),
              ],
            ],
          ),
        ),
      ),
      actions: [
        TextButton(
          onPressed: () => Navigator.pop(context),
          child: const Text('Cancel'),
        ),
        FilledButton(
          key: const ValueKey('send-offer'),
          onPressed: target == null
              ? null
              : () {
                  c.command('offer', {
                    'target': target,
                    'give': {
                      'pesos': int.tryParse(give.text) ?? -1,
                      'cards': selected
                          .map((key) => c.game!.instances[key])
                          .toList(),
                    },
                    'receive': loan
                        ? {}
                        : {
                            'pesos': int.tryParse(receive.text) ?? -1,
                            'cards': requested,
                          },
                    if (loan) 'loan_rounds': int.tryParse(rounds.text) ?? 0,
                  });
                  Navigator.pop(context);
                },
          child: const Text('Send proposal'),
        ),
      ],
    );
  }
}

class SocialView extends StatefulWidget {
  final AppController c;
  const SocialView(this.c, {super.key});
  @override
  State<SocialView> createState() => _SocialState();
}

class _SocialState extends State<SocialView> {
  final query = TextEditingController();
  bool friendsOnly = false;
  @override
  void dispose() {
    query.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) => AnimatedBuilder(
    animation: widget.c,
    builder: (context, _) => Scaffold(
      appBar: AppBar(title: const Text('Friends and rankings')),
      body: ListView(
        padding: const EdgeInsets.all(16),
        children: [
          if (widget.c.error != null) Text(widget.c.error!),
          TextField(
            controller: query,
            decoration: const InputDecoration(labelText: 'Search username'),
          ),
          OutlinedButton(
            onPressed: () => widget.c.search(query.text),
            child: const Text('Search'),
          ),
          for (final player in widget.c.foundPlayers)
            ListTile(
              title: Text(player['username']),
              trailing: TextButton(
                onPressed: () => widget.c.friendAction('request', player['id']),
                child: const Text('Request friendship'),
              ),
            ),
          for (final friend in widget.c.friends)
            ListTile(
              title: Text('${friend['sender']} ↔ ${friend['target']}'),
              subtitle: Text(
                friend['accepted'] == 1 ? 'Friends' : 'Pending request',
              ),
              trailing: Wrap(
                children: [
                  if (friend['accepted'] == 0 &&
                      friend['target'] == widget.c.id)
                    TextButton(
                      onPressed: () =>
                          widget.c.friendAction('accept', friend['sender']),
                      child: const Text('Accept'),
                    ),
                  TextButton(
                    onPressed: () => widget.c.friendAction(
                      'remove',
                      friend['sender'] == widget.c.id
                          ? friend['target']
                          : friend['sender'],
                    ),
                    child: Text(friend['accepted'] == 1 ? 'Remove' : 'Decline'),
                  ),
                ],
              ),
            ),
          const Text('Monthly Ranking Points (UTC)'),
          SwitchListTile(
            title: const Text('Friends leaderboard'),
            value: friendsOnly,
            onChanged: (value) {
              setState(() => friendsOnly = value);
              widget.c.social(friendsOnly: value);
            },
          ),
          for (var i = 0; i < widget.c.rankings.length; i++)
            ListTile(
              title: Text('${i + 1}. ${widget.c.rankings[i]['player']}'),
              trailing: Text(
                '${widget.c.rankings[i]['ranking_points']} Ranking Points',
              ),
            ),
          OutlinedButton(
            onPressed: widget.c.social,
            child: const Text('Refresh friends and rankings'),
          ),
        ],
      ),
    ),
  );
}

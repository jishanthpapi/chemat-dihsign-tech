"""Transactional SQLite authority: identity, consent, state, receipts and rankings."""
from contextlib import contextmanager
from datetime import datetime, timezone
import hashlib
import hmac
import json
from pathlib import Path
import secrets
import sqlite3
import uuid
import time
import unicodedata

from .engine import RuleError
from .match import Match, require, positive

AWARDS = {1: 30, 2: 15, 3: 5, 4: 0}


def season(now):
    return datetime.fromtimestamp(now, timezone.utc).strftime('%Y-%m')


class Store:
    def __init__(self, path, turn_seconds=60, negotiation_seconds=30):
        self.path = str(path)
        self.turn_seconds = positive(turn_seconds)
        self.negotiation_seconds = positive(negotiation_seconds)
        Path(self.path).parent.mkdir(parents=True, exist_ok=True)
        with self.db() as db:
            db.executescript('''
                CREATE TABLE IF NOT EXISTS players(id TEXT PRIMARY KEY, username TEXT NOT NULL,
                    username_key TEXT UNIQUE NOT NULL, credential TEXT NOT NULL);
                CREATE TABLE IF NOT EXISTS friends(sender TEXT NOT NULL, target TEXT NOT NULL,
                    accepted INTEGER NOT NULL DEFAULT 0, PRIMARY KEY(sender,target));
                CREATE TABLE IF NOT EXISTS lobbies(code TEXT PRIMARY KEY, owner TEXT NOT NULL,
                    public INTEGER NOT NULL, members TEXT NOT NULL, match_id TEXT);
                CREATE TABLE IF NOT EXISTS matches(id TEXT PRIMARY KEY, version INTEGER NOT NULL, state TEXT NOT NULL);
                CREATE TABLE IF NOT EXISTS receipts(match_id TEXT, player TEXT, request TEXT,
                    fingerprint TEXT NOT NULL, PRIMARY KEY(match_id,player,request));
                CREATE TABLE IF NOT EXISTS results(match_id TEXT PRIMARY KEY, season TEXT NOT NULL,
                    completed_at REAL NOT NULL, placements TEXT NOT NULL);
                CREATE TABLE IF NOT EXISTS awards(match_id TEXT, player TEXT, season TEXT NOT NULL,
                    points INTEGER NOT NULL, PRIMARY KEY(match_id,player));
                CREATE TABLE IF NOT EXISTS sessions(token TEXT PRIMARY KEY, player TEXT NOT NULL, expires REAL NOT NULL);
                CREATE TABLE IF NOT EXISTS schema_versions(version INTEGER PRIMARY KEY);
            ''')
            columns={r['name'] for r in db.execute('PRAGMA table_info(players)')}
            if 'revoked' not in columns:
                db.execute('ALTER TABLE players ADD COLUMN revoked INTEGER NOT NULL DEFAULT 0')
            columns={r['name'] for r in db.execute('PRAGMA table_info(lobbies)')}
            for name,definition in [('created','REAL NOT NULL DEFAULT 0'),('status',"TEXT NOT NULL DEFAULT 'open'"),('ready',"TEXT NOT NULL DEFAULT '[]'"),('presence',"TEXT NOT NULL DEFAULT '{}'")]:
                if name not in columns:
                    db.execute(f'ALTER TABLE lobbies ADD COLUMN {name} {definition}')
            db.execute('INSERT OR IGNORE INTO schema_versions VALUES(3)')
            db.execute('INSERT OR IGNORE INTO schema_versions VALUES(4)')

    @contextmanager
    def db(self):
        db = sqlite3.connect(self.path, timeout=15)
        db.row_factory = sqlite3.Row
        db.execute('PRAGMA foreign_keys=ON')
        try:
            db.execute('BEGIN IMMEDIATE')
            yield db
            db.commit()
        except Exception:
            db.rollback()
            raise
        finally:
            db.close()

    def register(self, username):
        require(isinstance(username, str) and 1 <= len(username.strip()) <= 32, 'Username must have 1–32 characters')
        username = unicodedata.normalize('NFC',username.strip())
        require(not any(unicodedata.category(c).startswith('C') for c in username), 'Username contains unsupported control characters')
        pid, token = str(uuid.uuid4()), secrets.token_urlsafe(32)
        try:
            with self.db() as db:
                db.execute('INSERT INTO players(id,username,username_key,credential) VALUES(?,?,?,?)',
                           (pid, username, username.casefold(), hashlib.sha256(token.encode()).hexdigest()))
        except sqlite3.IntegrityError as exc:
            raise RuleError('Username unavailable') from exc
        return dict(player_id=pid, credential=token, username=username)

    def authenticate(self, pid, token, now=None):
        require(isinstance(pid, str) and isinstance(token, str), 'Invalid credentials')
        with self.db() as db:
            row = db.execute('SELECT credential,revoked FROM players WHERE id=?', (pid,)).fetchone()
            session = db.execute('SELECT expires FROM sessions WHERE player=? AND token=?', (pid,hashlib.sha256(token.encode()).hexdigest())).fetchone()
        require(row is not None and not row['revoked'] and (hmac.compare_digest(row['credential'], hashlib.sha256(token.encode()).hexdigest()) or session is not None and session['expires']>(time.time() if now is None else now)), 'Invalid credentials')
        return pid

    def session(self,pid,credential,now):
        self.authenticate(pid,credential,now)
        token=secrets.token_urlsafe(32)
        with self.db() as db:
            db.execute('INSERT INTO sessions VALUES(?,?,?)',(hashlib.sha256(token.encode()).hexdigest(),pid,now+900))
        return {'access_token':token,'expires_at':now+900}

    def revoke(self,pid):
        with self.db() as db:
            db.execute('UPDATE players SET revoked=1 WHERE id=?',(pid,))
            db.execute('DELETE FROM sessions WHERE player=?',(pid,))

    def profile(self,pid):
        with self.db() as db:
            return dict(db.execute('SELECT id,username FROM players WHERE id=?',(pid,)).fetchone())

    def available(self,username):
        with self.db() as db:
            return db.execute('SELECT 1 FROM players WHERE username_key=?',(unicodedata.normalize('NFC',username.strip()).casefold(),)).fetchone() is None

    def search(self,query):
        with self.db() as db:
            return [dict(r) for r in db.execute('SELECT id,username FROM players WHERE instr(username_key,?)>0 LIMIT 20',(query.strip().casefold(),))]

    def rename(self, pid, username):
        require(isinstance(username, str) and 1 <= len(username.strip()) <= 32, 'Invalid username')
        username=unicodedata.normalize('NFC',username.strip())
        require(not any(unicodedata.category(c).startswith('C') for c in username), 'Username contains unsupported control characters')
        try:
            with self.db() as db:
                db.execute('UPDATE players SET username=?,username_key=? WHERE id=?', (username.strip(), username.strip().casefold(), pid))
        except sqlite3.IntegrityError as exc:
            raise RuleError('Username unavailable') from exc

    def friend_request(self, pid, target):
        require(isinstance(target,str), 'Invalid target')
        with self.db() as db:
            row = db.execute('SELECT id FROM players WHERE id=? OR username_key=?', (target, target.casefold())).fetchone()
            require(row is not None and row['id'] != pid, 'Choose another registered player')
            target = row['id']
            require(not db.execute('SELECT 1 FROM friends WHERE (sender=? AND target=?) OR (sender=? AND target=?)', (pid,target,target,pid)).fetchone(), 'Request or friendship already exists')
            db.execute('INSERT INTO friends(sender,target) VALUES(?,?)', (pid,target))

    def friend_accept(self, pid, sender):
        with self.db() as db:
            require(db.execute('UPDATE friends SET accepted=1 WHERE sender=? AND target=? AND accepted=0', (sender,pid)).rowcount == 1, 'No incoming request')

    def friends(self, pid):
        with self.db() as db:
            rows = db.execute('SELECT sender,target,accepted FROM friends WHERE sender=? OR target=?', (pid,pid)).fetchall()
        return [dict(r) for r in rows]

    def remove_friend(self,pid,other):
        with self.db() as db:
            db.execute('DELETE FROM friends WHERE (sender=? AND target=?) OR (sender=? AND target=?)',(pid,other,other,pid))

    def _eligible(self,db,pid):
        for row in db.execute("SELECT * FROM lobbies WHERE status='open' OR match_id IS NOT NULL"):
            if pid not in json.loads(row['members']):
                continue
            if row['match_id']:
                _,match=self._load(db,row['match_id'])
                require(match.phase=='finished' or not match.players[pid].active,'Already in an active match')
            else:
                raise RuleError('Already in an open lobby')

    def lobby(self, pid, public=False, now=None):
        with self.db() as db:
            self._eligible(db,pid)
            code = secrets.token_hex(4).upper()
            while db.execute('SELECT 1 FROM lobbies WHERE code=?',(code,)).fetchone():
                code=secrets.token_hex(4).upper()
            stamp=time.time() if now is None else now
            db.execute('INSERT INTO lobbies(code,owner,public,members,created,presence) VALUES(?,?,?,?,?,?)', (code,pid,int(public),json.dumps([pid]),stamp,json.dumps({pid:stamp})))
        return code

    def join(self, pid, code, now=None):
        with self.db() as db:
            row = db.execute('SELECT * FROM lobbies WHERE code=?', (code,)).fetchone()
            require(row is not None and row['match_id'] is None, 'Lobby unavailable')
            require(row['status']=='open','Lobby closed')
            self._eligible(db,pid)
            members = json.loads(row['members'])
            require(pid not in members and len(members) < 4, 'Already joined or lobby full')
            members.append(pid)
            presence=json.loads(row['presence']);presence[pid]=time.time() if now is None else now
            db.execute('UPDATE lobbies SET members=?,presence=? WHERE code=?', (json.dumps(members),json.dumps(presence),code))

    def matchmaking(self, pid, now=None):
        stamp=time.time() if now is None else now
        with self.db() as db:
            for existing in db.execute("SELECT * FROM lobbies WHERE status='open'"):
                if pid in json.loads(existing['members']):
                    require(existing['public'],'Already in private lobby')
                    return existing['code']
            self._eligible(db,pid)
            for row in db.execute("SELECT * FROM lobbies WHERE public=1 AND match_id IS NULL AND status='open' ORDER BY rowid"):
                members = json.loads(row['members'])
                if pid in members:
                    return row['code']
                if len(members) < 4:
                    members.append(pid)
                    presence=json.loads(row['presence']);presence[pid]=stamp
                    db.execute('UPDATE lobbies SET members=?,presence=? WHERE code=?', (json.dumps(members),json.dumps(presence),row['code']))
                    return row['code']
            code = secrets.token_hex(4).upper()
            while db.execute('SELECT 1 FROM lobbies WHERE code=?',(code,)).fetchone():
                code=secrets.token_hex(4).upper()
            db.execute('INSERT INTO lobbies(code,owner,public,members,created,presence) VALUES(?,?,?,?,?,?)', (code,pid,1,json.dumps([pid]),stamp,json.dumps({pid:stamp})))
            return code

    def lobby_view(self, pid, code, now=None):
        with self.db() as db:
            row = db.execute('SELECT * FROM lobbies WHERE code=?', (code,)).fetchone()
            require(row is not None and pid in json.loads(row['members']), 'Not a lobby member')
            members=json.loads(row['members'])
            if row['status']=='open':
                presence=json.loads(row['presence']);presence[pid]=time.time() if now is None else now
                db.execute('UPDATE lobbies SET presence=? WHERE code=?',(json.dumps(presence),code))
            return dict(code=code,owner=row['owner'],members=members,match_id=row['match_id'],status=row['status'],created_at=row['created'],ready=json.loads(row['ready']),
                        usernames={p:db.execute('SELECT username FROM players WHERE id=?',(p,)).fetchone()[0] for p in members})

    def lobby_change(self,pid,code,operation):
        with self.db() as db:
            row=db.execute('SELECT * FROM lobbies WHERE code=?',(code,)).fetchone()
            require(row is not None and row['status']=='open','Lobby closed')
            members=json.loads(row['members'])
            ready=set(json.loads(row['ready']))
            require(pid in members,'Not a member')
            if operation=='leave':
                members.remove(pid)
                ready.discard(pid)
                db.execute('UPDATE lobbies SET owner=?,status=? WHERE code=?',(members[0] if members else pid,'open' if members else 'cancelled',code))
            elif operation=='cancel':
                require(row['owner']==pid,'Only host may cancel')
                db.execute("UPDATE lobbies SET status='cancelled' WHERE code=?",(code,))
            elif operation=='ready':
                ready.add(pid)
            elif operation=='unready':
                ready.discard(pid)
            else:
                raise RuleError('Unknown lobby operation')
            db.execute('UPDATE lobbies SET members=?,ready=? WHERE code=?',(json.dumps(members),json.dumps(sorted(ready)),code))

    def start(self, pid, code, now, require_ready=False):
        with self.db() as db:
            row = db.execute('SELECT * FROM lobbies WHERE code=?', (code,)).fetchone()
            require(row is not None and row['owner'] == pid and row['match_id'] is None, 'Only owner may start an unstarted lobby')
            require(row['status']=='open','Lobby closed')
            if require_ready:
                require(set(json.loads(row['members']))==set(json.loads(row['ready'])),'All players must be ready')
            match = Match(json.loads(row['members']), secrets.randbits(64), now, self.turn_seconds, self.negotiation_seconds)
            mid = str(uuid.uuid4())
            db.execute('INSERT INTO matches VALUES(?,0,?)', (mid,json.dumps(match.to_state())))
            db.execute("UPDATE lobbies SET match_id=?,status='started' WHERE code=?", (mid,code))
            return mid

    def _load(self, db, mid):
        row = db.execute('SELECT * FROM matches WHERE id=?', (mid,)).fetchone()
        require(row is not None, 'Unknown match')
        return row['version'], Match.from_state(json.loads(row['state']))

    def view(self, pid, mid):
        with self.db() as db:
            version, match = self._load(db, mid)
            return dict(version=version, state=match.snapshot(pid))

    def _save(self, db, mid, version, match, now):
        db.execute('UPDATE matches SET version=?,state=? WHERE id=?', (version,json.dumps(match.to_state()),mid))
        if match.phase == 'finished' and not match.result_blocked:
            placements = {p: x.placement for p,x in match.players.items()}
            require(sorted(placements.values()) == list(range(1,len(placements)+1)), 'Invalid authoritative placements')
            if db.execute('INSERT OR IGNORE INTO results VALUES(?,?,?,?)', (mid,season(now),now,json.dumps(placements))).rowcount:
                for pid, place in placements.items():
                    db.execute('INSERT INTO awards VALUES(?,?,?,?)', (mid,pid,season(now),0 if match.players[pid].forfeited else AWARDS[place]))

    def command(self, pid, mid, request, expected, name, args, now):
        require(isinstance(request, str) and 1 <= len(request) <= 100, 'Invalid request ID')
        require(type(expected) is int and isinstance(args, dict) and isinstance(name,str), 'Invalid command envelope')
        fingerprint = hashlib.sha256(json.dumps([name,args],sort_keys=True).encode()).hexdigest()
        with self.db() as db:
            version, match = self._load(db, mid)
            require(pid in match.players, 'Not a match participant')
            old = db.execute('SELECT fingerprint FROM receipts WHERE match_id=? AND player=? AND request=?', (mid,pid,request)).fetchone()
            if old:
                require(old['fingerprint'] == fingerprint, 'Request ID reused for different command')
                return dict(version=version, state=match.snapshot(pid), duplicate=True)
            require(version == expected, 'Stale match version')
            if (match.choice and now >= match.choice['deadline']) or (not match.choice and match.phase in ('regular','reaction') and now >= match.deadline):
                before = match.to_state()
                match.tick(now)
                if match.to_state() != before:
                    self._save(db, mid, version+1, match, now)
                    return dict(version=version+1, state=match.snapshot(pid), expired=True)
            match.command(pid, name, args, now)
            self._save(db, mid, version+1, match, now)
            db.execute('INSERT INTO receipts VALUES(?,?,?,?)', (mid,pid,request,fingerprint))
            return dict(version=version+1, state=match.snapshot(pid), duplicate=False)

    def connection(self, pid, mid, now, connected):
        with self.db() as db:
            version, match = self._load(db, mid)
            (match.reconnect if connected else match.disconnect)(pid, now)
            self._save(db, mid, version+1, match, now)

    def tick_all(self, now):
        with self.db() as db:
            db.execute("UPDATE lobbies SET status='expired' WHERE status='open' AND created>0 AND created+1800<=?",(now,))
            for lobby in db.execute("SELECT * FROM lobbies WHERE status='open'").fetchall():
                presence=json.loads(lobby['presence'])
                if presence and presence.get(lobby['owner'],lobby['created'])+90<=now:
                    candidates=[p for p in json.loads(lobby['members']) if presence.get(p,0)+90>now]
                    if candidates:
                        db.execute('UPDATE lobbies SET owner=? WHERE code=?',(candidates[0],lobby['code']))
            for row in db.execute('SELECT id,version,state FROM matches').fetchall():
                match = Match.from_state(json.loads(row['state']))
                before = match.to_state()
                try:
                    match.tick(now)
                except RuleError:
                    continue
                if match.to_state() != before:
                    self._save(db,row['id'],row['version']+1,match,now)

    def leaderboard(self, now):
        with self.db() as db:
            return [dict(r) for r in db.execute('SELECT player, SUM(points) AS ranking_points FROM awards WHERE season=? GROUP BY player ORDER BY ranking_points DESC,player', (season(now),))]

    def friends_leaderboard(self,pid,now):
        rows=self.friends(pid)
        eligible={pid}|{r['target'] if r['sender']==pid else r['sender'] for r in rows if r['accepted']}
        return [r for r in self.leaderboard(now) if r['player'] in eligible]

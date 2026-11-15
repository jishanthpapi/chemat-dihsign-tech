# Multiplayer protocol

Local development service: http://127.0.0.1:8000. Hosted services require HTTPS/WSS. Run a single worker. /docs contains the OpenAPI routes.

1. POST /players with {"username":"Alice"} returns player_id and a one-time credential. Store that credential securely. Username uniqueness is case insensitive. PATCH /players/me edits a username.
2. Authenticated HTTP requests require X-Player-ID and X-Device-Credential headers. IDs alone are rejected. The future Flutter layer must keep credentials in OS secure storage, not local profile SQLite.
3. POST /lobbies with {} creates a private code. POST /lobbies/{code}/join joins by invitation. POST /matchmaking joins or creates a public lobby. GET /lobbies/{code} shows members and match ID to members only. The owner POSTs /lobbies/{code}/start once 2–4 players have joined.
4. GET /matches/{id} returns version and viewer-specific state. POST /matches/{id}/commands accepts {"request_id":"unique-device-request-1","version":0,"command":"end_turn","args":{}}. Use the latest version. A stale command returns 409; refresh and reconsider the intent. Identical duplicate requests do not repeat effects. An expired turn response has expired=true and does not apply the requested command.
5. WebSocket /matches/{id}/ws: first message is {"player_id":"...","credential":"..."}. Subsequent messages use the same command envelope. Replies include a receipt followed by per-viewer broadcast snapshots. Errors contain error. First-message authentication has a ten-second timeout. Reconnect receives a current authorized snapshot; client backoff/reconnect UI is future work.

## Commands and arguments
- buy: kind (reactant/apparatus/action)
- bank: amount, optional withdraw boolean
- offer: target, give/receive {pesos,cards}, optional loan_rounds. Cards are [deck,name] pairs. Omit receive for a gift. Loans require no reciprocal resources. The target must accept before the configurable negotiation deadline.
- accept: offer ID
- substitute: loan ID, pesos; lender approval only, including an exited lender. Borrower accepts by choosing substitution on repayment.
- repay: loan ID, optional substitute boolean. Full selected debt settlement; no forced debt ordering.
- play: card name, target when required; only own regular turn, costs 2 pesos and queues effects.
- choose: selected array matching the private choice options/count. Counter-Reaction decline is [null]; redirect is [player ID]. Card selections are arrays of [deck,name] pairs. Unknown, repeated-unavailable or wrong-owner choices are rejected.
- create: compound name from own active Task
- replace: no args, once per reaction opportunity
- end_turn / end_reaction: no args

GET /friends returns request rows with accepted=0/1; only accepted rows represent friendships. POST /friends/request uses target ID or username. POST /friends/accept uses sender ID and only the recipient may accept. GET /leaderboard returns current UTC-month Ranking Points, distinct from match_points and pesos.

CHEMAT_DATABASE_PATH, CHEMAT_TURN_SECONDS (default 60), CHEMAT_NEGOTIATION_SECONDS (default 30) configure the server. Timers must be positive integers. Reconnection grace is 90 seconds. Three consecutive missed regular turns mark a forfeit; successful end_turn resets the streak. Timed-out reactions pass. Mandatory selections remain pending after timeout and may be explicitly answered late; optional redirects default to decline. This avoids inventing resource choices but means mandatory choices can stall a match.

Loan due checkpoint: round created + agreed rounds - 1. Immediately after that entire round (including mini-rounds) finishes, unpaid loans gain 2-peso penalty; each later overdue round adds 2. Repayments to exited lenders enter persistent match escrow, not the bank. Escrow is visible to its owner; no cross-match currency is created.

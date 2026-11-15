# Amendment implementation and test index

Original rules and new amendment precedence were audited before coding in RULEBOOK_MAPPING.md. Raw source exports are unchanged. The tests below exercise amended behavior; fixtures are clearly distinguished from legal full matches.

| Amendments | Code | Explicit tests |
|---|---|---|
| A1, A4 | Match.offer/accept/substitute/repay | test_A1_A4_same_named_card_substitution_and_borrower_order |
| A2, A3 | _next_mini/_complete_round | test_A2_A3_deadline_after_all_minis_and_lender_penalties |
| A5, A6 | _transfer/_placement/_exit_if_ready | test_A5_A6_placed_borrower_frozen_and_exited_lender_escrow; test_A5_card_repayment_to_exited_lender_escrow; test_A6_frozen_compounds_zero_reward_and_debt_stays; test_own_turn_debt_settlement_advances_exited_player |
| A7, A8 | _advance_attack/choose | test_A7_A8_optional_redirect_chain_terminates_and_consumes; test_A7_decline_and_expiry; test_A8_storage_before_counter_goggles_and_chaos_immune |
| A8, A9 | _advance_attack/_consume | test_A8_A9_backup_before_insurance_and_coexistence; test_A9_insurance_after_two_actual_losses; test_A9_redirected_area_attack_insurance_aggregates_actual_losses |
| A10 | attacker-owned attack_select | test_A10_attacker_selects_equipment |
| A11 | queued reverse_count, round completion | test_A11_sequential_reversal_effective_next_round (1/2/3 copies) |
| A12 | simultaneous outgoing snapshot | test_A12_simultaneous_shuffle_empty_hands |
| A13 | private research draw/select | test_A13_research_partial_supply (0–5 available) |
| A14 | missing Task retry at next opportunity | test_A14_empty_task_supply_and_recovery |
| A15 | replacement flag and lifetime counter | test_A15_replacement_once_and_lifetime_escalation |
| A16 | economy window checks | test_A16_cutoff_at_creation_atomic_failures_and_all_pass_boundary; test_mini_trade_initiation_and_negotiation_expiry |
| A17 | bank net-flow accounting | test_A17_unlimited_bank_and_state_roundtrip |
| D1, D2 | Store._save/leaderboard/season | test_D1_D2_rankings_verified_once_and_utc_month_reset; test_api_rejects_client_supplied_results_and_persists_earned_result |
| D3 | friend request and recipient acceptance | test_D3_friend_request_requires_target_acceptance |
| D4 | register/authenticate/rename and routes | test_D4_unique_names_authenticated_ids_and_no_plaintext_credentials |
| D5, D6 | disconnect/reconnect/tick | test_D5_D6_D7_reconnect_grace_and_missed_streak; test_D5_durable_disconnect_reconnect_boundary |
| D7 | configurable positive timers | test_D7_server_timers_cannot_be_bypassed; test_missed_streak_reset_and_positive_timers |
| D8 | transactional JSON snapshots and receipts | test_D8_atomic_persistence_receipts_restart_and_versions; test_D8_simultaneous_commands_one_wins; test_D8_pending_private_choice_survives_restart_and_late_response |

Integration tests also exercise accepted friendship/username flow, lobby matchmaking, authenticated WebSocket commands, viewer redaction, broadcasts, reconnect snapshots and blocked forfeit ranking awards. Full legal-command simulations cover seeds 7/19 for 2/3/4 players, with repeated deterministic outcomes and per-step resource conservation. These use no injected resources or fabricated outcomes. Near-terminal/attack/debt tests explicitly use controlled fixtures to reach specific edge cases.

Remaining limitations: mobile profile/connectivity work, mandatory-selection timeout policy, forfeit placement/debt policy and deployment/native validation. No custom UI or artwork was added.

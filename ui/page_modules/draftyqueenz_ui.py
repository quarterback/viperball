"""
DraftyQueenz UI components for the Play tab.

Renders pre-sim betting/fantasy and post-sim results inline
within the weekly simulation flow.

Key UX improvements over the original:
- st.form wraps all bet/draft/donate inputs so selections don't trigger
  page reruns until the user explicitly submits
- Odds board shows all games at a glance before picking
- Horizontal radio buttons for bet type and pick reduce clicks
- Salary cap progress bar for fantasy drafting
- Roster displayed as a visual card grid
- Real st.progress bars for donation boosts
"""

import streamlit as st
from ui import api_client


# ---------------------------------------------------------------------------
# DQ-specific CSS injected once per render cycle
# ---------------------------------------------------------------------------

_DQ_CSS = """
<style>
.dq-odds-card {
    background: #f8fafc;
    border: 1px solid #e2e8f0;
    border-radius: 10px;
    padding: 10px 14px;
    margin-bottom: 6px;
    font-size: 0.88rem;
    line-height: 1.45;
}
.dq-odds-card .matchup {
    font-weight: 700;
    color: #0f172a;
    margin-bottom: 2px;
}
.dq-odds-card .lines {
    color: #64748b;
    font-size: 0.82rem;
}
.dq-slip {
    background: #fffbeb;
    border: 1px solid #fbbf24;
    border-radius: 8px;
    padding: 12px 16px;
    margin-top: 8px;
}
.dq-slip .slip-title {
    font-weight: 700;
    color: #92400e;
    font-size: 0.85rem;
    text-transform: uppercase;
    letter-spacing: 0.04em;
    margin-bottom: 4px;
}
.dq-slip .slip-row {
    color: #78350f;
    font-size: 0.9rem;
}
.dq-roster-slot {
    background: #f8fafc;
    border: 1px solid #e2e8f0;
    border-radius: 8px;
    padding: 8px 12px;
    text-align: center;
    min-height: 68px;
}
.dq-roster-slot .slot-label {
    font-weight: 700;
    font-size: 0.75rem;
    color: #94a3b8;
    text-transform: uppercase;
    letter-spacing: 0.05em;
}
.dq-roster-slot .slot-player {
    font-weight: 600;
    color: #0f172a;
    font-size: 0.9rem;
}
.dq-roster-slot .slot-meta {
    color: #64748b;
    font-size: 0.78rem;
}
.dq-roster-slot.empty {
    border-style: dashed;
    border-color: #cbd5e1;
}
.dq-roster-slot.empty .slot-player {
    color: #94a3b8;
    font-style: italic;
}
.dq-tier-badge {
    display: inline-block;
    background: linear-gradient(135deg, #fbbf24, #f59e0b);
    color: #78350f;
    font-weight: 700;
    font-size: 0.85rem;
    padding: 4px 12px;
    border-radius: 20px;
}
</style>
"""


def _inject_dq_css():
    """Inject DQ styling once per page render."""
    if not st.session_state.get("_dq_css_injected"):
        st.markdown(_DQ_CSS, unsafe_allow_html=True)
        st.session_state["_dq_css_injected"] = True


# ---------------------------------------------------------------------------
# Public entry points (API unchanged — drop-in replacement)
# ---------------------------------------------------------------------------

def render_dq_bankroll_banner(session_id: str):
    try:
        status = api_client.dq_status(session_id)
    except api_client.APIError:
        return

    bal = status.get("bankroll", 0)
    tier = status.get("booster_tier", "Sideline Pass")
    roi = status.get("roi", 0)

    c1, c2, c3 = st.columns(3)
    c1.metric("DQ$ Balance", f"${bal:,}")
    c2.metric("Booster Tier", tier)
    c3.metric("ROI", f"{roi:+.1f}%")


def render_dq_pre_sim(session_id: str, next_week: int, key_prefix: str = ""):
    _inject_dq_css()

    try:
        start_resp = api_client.dq_start_week(session_id, next_week)
    except api_client.APIError as e:
        st.warning(f"DraftyQueenz unavailable: {e.detail}")
        return

    # Always-visible container instead of a collapsed expander
    st.markdown(f"#### DraftyQueenz — Week {next_week}")

    tab_pred, tab_fantasy, tab_donate = st.tabs(
        ["Predictions", "Fantasy", "Donate"]
    )

    with tab_pred:
        _render_predictions_tab(session_id, next_week, key_prefix)

    with tab_fantasy:
        _render_fantasy_tab(session_id, next_week, key_prefix)

    with tab_donate:
        _render_donate_tab(session_id, key_prefix)


# ---------------------------------------------------------------------------
# Predictions tab
# ---------------------------------------------------------------------------

def _render_predictions_tab(session_id: str, week: int, kp: str):
    try:
        odds_resp = api_client.dq_get_odds(session_id, week)
    except api_client.APIError:
        st.error("Could not load odds.")
        return

    try:
        status = api_client.dq_status(session_id)
        balance = status.get("bankroll", 0)
    except api_client.APIError:
        balance = 0

    odds_list = odds_resp.get("odds", [])
    if not odds_list:
        st.info("No games available for predictions this week.")
        return

    # -- Balance bar ----------------------------------------------------------
    st.caption(f"Balance: **${balance:,} DQ$** | Min $250 | Max $25,000")

    # -- Existing picks -------------------------------------------------------
    try:
        contest_resp = api_client.dq_get_contest(session_id, week)
        existing_picks = contest_resp.get("picks", [])
        existing_parlays = contest_resp.get("parlays", [])
    except api_client.APIError:
        existing_picks = []
        existing_parlays = []

    if existing_picks or existing_parlays:
        with st.container(border=True):
            if existing_picks:
                st.markdown("**Your Picks**")
                for p in existing_picks:
                    icon = ""
                    if p.get("result") == "win":
                        icon = " ✓"
                    elif p.get("result") == "loss":
                        icon = " ✗"
                    st.markdown(
                        f"- {p['pick_type'].title()}: **{p['selection']}** "
                        f"on {p['matchup']} — ${p['amount']:,}{icon}"
                    )

            if existing_parlays:
                st.markdown("**Your Parlays**")
                for pl in existing_parlays:
                    legs_str = ", ".join(
                        l['selection'] for l in pl.get("legs", [])
                    )
                    st.markdown(
                        f"- {len(pl.get('legs', []))}-leg "
                        f"({pl['multiplier']}x): {legs_str} — ${pl['amount']:,}"
                    )

    # -- Odds board (all games at a glance) -----------------------------------
    st.markdown("**This Week's Lines**")
    _render_odds_board(odds_list)

    # -- Place-a-Bet form (no reruns until submit) ----------------------------
    st.divider()
    st.markdown("**Place a Bet**")

    if balance < 250:
        st.warning("Insufficient balance to place a bet (need at least $250).")
        return

    game_labels = [
        f"{o['away_team']} @ {o['home_team']}"
        for o in odds_list
    ]

    bet_type_labels = {
        "winner": "Winner",
        "spread": "Spread",
        "over_under": "Over / Under",
        "chaos": "Chaos Factor",
        "kick_pass": "Kick Pass O/U",
    }
    bet_type_keys = list(bet_type_labels.keys())

    with st.form(key=f"{kp}dq_bet_form", clear_on_submit=False, border=True):
        # Row 1 — Game selector
        game_idx = st.selectbox(
            "Game",
            range(len(game_labels)),
            format_func=lambda i: game_labels[i],
            key=f"{kp}dq_game_select",
        )

        # Row 2 — Bet type as horizontal radio
        pick_type = st.radio(
            "Bet Type",
            bet_type_keys,
            format_func=lambda k: bet_type_labels[k],
            horizontal=True,
            key=f"{kp}dq_pick_type",
        )

        # Row 3 — Show relevant odds for the selected game
        sel_odds = odds_list[game_idx] if game_idx is not None else None
        if sel_odds:
            oc1, oc2, oc3 = st.columns(3)
            oc1.markdown(f"**Spread:** {sel_odds['spread']:+.1f}")
            oc2.markdown(f"**O/U:** {sel_odds['over_under']:.1f}")
            oc3.markdown(
                f"**KP O/U:** {sel_odds.get('kick_pass_ou', 14.5):.1f}"
            )

        # Row 4 — Pick as horizontal radio
        if sel_odds:
            if pick_type in ("winner", "spread"):
                pick_options = [sel_odds["home_team"], sel_odds["away_team"]]
            else:
                pick_options = ["over", "under"]
        else:
            pick_options = ["over", "under"]

        selection = st.radio(
            "Pick",
            pick_options,
            horizontal=True,
            key=f"{kp}dq_selection",
        )

        # Row 5 — Wager slider + fine-tune input side by side
        max_wager = min(25000, balance)
        default_wager = min(500, max_wager)
        wc1, wc2 = st.columns([3, 1])
        with wc1:
            amount = st.slider(
                "Wager (DQ$)",
                min_value=250,
                max_value=max_wager,
                value=default_wager,
                step=250,
                key=f"{kp}dq_bet_amount",
            )
        with wc2:
            amount = st.number_input(
                "Exact",
                min_value=250,
                max_value=max_wager,
                value=amount,
                step=250,
                key=f"{kp}dq_bet_exact",
            )

        submitted = st.form_submit_button(
            "Place Bet", type="primary", use_container_width=True
        )

    if submitted:
        try:
            resp = api_client.dq_place_pick(
                session_id, week, pick_type, game_idx, selection, amount
            )
            st.success(f"Bet placed! Balance: ${resp['bankroll']:,}")
            st.rerun()
        except api_client.APIError as e:
            st.error(e.detail)


def _render_odds_board(odds_list: list):
    """Compact 2-column odds board so users see all games before picking."""
    cols_per_row = 2
    for row_start in range(0, len(odds_list), cols_per_row):
        cols = st.columns(cols_per_row)
        for ci in range(cols_per_row):
            idx = row_start + ci
            if idx >= len(odds_list):
                break
            o = odds_list[idx]
            spread_str = f"{o['spread']:+.1f}"
            ou_str = f"{o['over_under']:.1f}"
            kp_ou = f"{o.get('kick_pass_ou', 14.5):.1f}"
            away_ml = o.get("away_ml_display", "")
            home_ml = o.get("home_ml_display", "")
            with cols[ci]:
                st.markdown(
                    f'<div class="dq-odds-card">'
                    f'<div class="matchup">{o["away_team"]} ({away_ml}) @ '
                    f'{o["home_team"]} ({home_ml})</div>'
                    f'<div class="lines">Spread {spread_str} · '
                    f'O/U {ou_str} · KP O/U {kp_ou}</div>'
                    f'</div>',
                    unsafe_allow_html=True,
                )


# ---------------------------------------------------------------------------
# Fantasy tab
# ---------------------------------------------------------------------------

def _render_fantasy_tab(session_id: str, week: int, kp: str):
    try:
        roster_resp = api_client.dq_get_roster(session_id, week)
    except api_client.APIError:
        roster_resp = {"entered": False}

    entered = roster_resp.get("entered", False)

    if not entered:
        with st.container(border=True):
            st.markdown("**Weekly Fantasy** — Entry fee: $2,500 DQ$")
            st.markdown(
                "Draft a 5-player salary-capped roster. "
                "Compete against 9 AI managers."
            )
            if st.button("Enter Fantasy ($2,500)", key=f"{kp}dq_enter_fantasy",
                         type="primary"):
                try:
                    api_client.dq_enter_fantasy(session_id, week)
                    st.success("Entered! Now draft your roster.")
                    st.rerun()
                except api_client.APIError as e:
                    st.error(e.detail)
        return

    roster_data = roster_resp.get("roster", {})
    entries = roster_data.get("entries", {})
    total_salary = roster_data.get("total_salary", 0)
    cap_remaining = 50000 - total_salary
    slots_filled = len(entries)

    # -- Salary cap progress bar ----------------------------------------------
    cap_pct = min(total_salary / 50000, 1.0)
    st.markdown(
        f"**Your Roster** ({slots_filled}/5) — "
        f"${total_salary:,} / $50,000 used — ${cap_remaining:,} remaining"
    )
    st.progress(cap_pct, text=f"Salary cap: {cap_pct:.0%}")

    # -- Roster card grid (5 slots in a row) ----------------------------------
    slot_names = ["VP", "BALL1", "BALL2", "KP", "FLEX"]
    slot_cols = st.columns(5)
    for i, slot in enumerate(slot_names):
        entry = entries.get(slot)
        with slot_cols[i]:
            if entry:
                st.markdown(
                    f'<div class="dq-roster-slot">'
                    f'<div class="slot-label">{slot}</div>'
                    f'<div class="slot-player">{entry["name"]}</div>'
                    f'<div class="slot-meta">{entry["team"]} · '
                    f'{entry["position"]}<br>${entry["salary"]:,}</div>'
                    f'</div>',
                    unsafe_allow_html=True,
                )
            else:
                st.markdown(
                    f'<div class="dq-roster-slot empty">'
                    f'<div class="slot-label">{slot}</div>'
                    f'<div class="slot-player">Empty</div>'
                    f'<div class="slot-meta">—</div>'
                    f'</div>',
                    unsafe_allow_html=True,
                )

    # -- Draft form (no reruns until submit) ----------------------------------
    st.divider()
    st.markdown("**Draft a Player**")

    # Position filter lives outside the form so the pool refreshes on change
    pos_filter = st.selectbox(
        "Filter by position",
        ["All", "VP", "HB", "ZB", "WB", "SB", "KP"],
        key=f"{kp}dq_pos_filter",
    )

    try:
        pool_pos = pos_filter if pos_filter != "All" else None
        pool_resp = api_client.dq_fantasy_pool(
            session_id, week, position=pool_pos
        )
        pool = pool_resp.get("pool", [])
    except api_client.APIError:
        pool = []

    if not pool:
        st.info("No players available for this position filter.")
        return

    player_labels = [
        f"{p['name']} ({p['team']}) [{p['position']}] "
        f"OVR:{p['overall']}  ${p['salary']:,}  proj:{p['projected']}"
        for p in pool
    ]

    with st.form(key=f"{kp}dq_draft_form", clear_on_submit=False, border=True):
        fc1, fc2 = st.columns([3, 1])
        with fc1:
            player_idx = st.selectbox(
                "Player",
                range(len(player_labels)),
                format_func=lambda i: player_labels[i],
                key=f"{kp}dq_player_select",
            )
        with fc2:
            slot_to_fill = st.selectbox(
                "Slot", slot_names, key=f"{kp}dq_slot_select"
            )

        draft_submitted = st.form_submit_button(
            "Draft Player", type="primary", use_container_width=True
        )

    if draft_submitted:
        selected = pool[player_idx]
        try:
            api_client.dq_set_roster_slot(
                session_id, week, slot_to_fill,
                selected["tag"], selected["team"],
            )
            st.success(f"Drafted {selected['name']} to {slot_to_fill}!")
            st.rerun()
        except api_client.APIError as e:
            st.error(e.detail)


# ---------------------------------------------------------------------------
# Donate tab
# ---------------------------------------------------------------------------

def _render_donate_tab(session_id: str, kp: str):
    try:
        portfolio = api_client.dq_portfolio(session_id)
    except api_client.APIError:
        st.info("DraftyQueenz portfolio unavailable.")
        return

    try:
        status = api_client.dq_status(session_id)
        balance = status.get("bankroll", 0)
    except api_client.APIError:
        balance = 0

    tier = portfolio.get("booster_tier", "Sideline Pass")
    tier_desc = portfolio.get("booster_tier_desc", "")
    career = portfolio.get("career_donated", 0)
    next_tier = portfolio.get("next_tier")

    # -- Tier badge -----------------------------------------------------------
    st.markdown(
        f'<span class="dq-tier-badge">{tier}</span> — {tier_desc}',
        unsafe_allow_html=True,
    )
    st.markdown(f"Career donated: **${career:,} DQ$**")
    if next_tier:
        needed = next_tier["amount_needed"]
        # Show progress toward next tier
        if career + needed > 0:
            tier_progress = career / (career + needed)
        else:
            tier_progress = 0.0
        st.progress(
            min(tier_progress, 1.0),
            text=f"Next: {next_tier['name']} (${needed:,} to go)",
        )

    # -- Active boosts with real progress bars --------------------------------
    human_teams = portfolio.get("human_teams", [])
    team_boosts = portfolio.get("team_boosts", {})

    if team_boosts:
        st.markdown("**Active Boosts by Program**")
        for team_name, boosts_list in team_boosts.items():
            active = [b for b in boosts_list if b.get("current_value", 0) > 0]
            if active:
                st.markdown(f"**{team_name}**")
                for b in active:
                    pct = b.get("progress_pct", 0)
                    st.progress(
                        min(pct / 100.0, 1.0),
                        text=f"{b['label']}: +{b['current_value']:.1f} ({pct:.0f}%)",
                    )
            else:
                st.markdown(f"**{team_name}** — no active boosts yet")
    elif human_teams:
        st.info("No donations made yet. Donate your DQ$ winnings to boost your program!")

    # -- Donation form --------------------------------------------------------
    st.divider()
    st.markdown(f"**Make a Donation** (Balance: ${balance:,} | Min: $10,000)")

    if not human_teams:
        st.warning(
            "No coached team found. Start a season or dynasty to donate."
        )
        return

    if balance < 10000:
        st.warning("Insufficient balance to donate (need at least $10,000).")
        return

    with st.form(key=f"{kp}dq_donate_form", clear_on_submit=False, border=True):
        target_team = st.selectbox(
            "Donate to Program", human_teams,
            key=f"{kp}dq_donate_team",
        )

        dtype_options = portfolio.get("donation_types", {})
        if dtype_options:
            dtype_keys = list(dtype_options.keys())
            dtype_labels = [dtype_options[k]["label"] for k in dtype_keys]
            dtype_idx = st.radio(
                "Donation Type",
                range(len(dtype_labels)),
                format_func=lambda i: (
                    f"{dtype_labels[i]} — "
                    f"{dtype_options[dtype_keys[i]]['description']}"
                ),
                key=f"{kp}dq_donate_type",
            )
        else:
            dtype_keys = []
            dtype_idx = 0

        min_donate = 1000
        if balance < min_donate:
            st.info(f"You need at least DQ${min_donate:,} to donate. Current balance: DQ${balance:,}.")
            donate_amount = 0
        else:
            max_donate = balance
            default_donate = min(10000, max_donate)
            slider_step = max(1, (max_donate - min_donate) // 100) if max_donate > min_donate else 1
            dc1, dc2 = st.columns([3, 1])
            with dc1:
                donate_amount = st.slider(
                    "Amount (DQ$)",
                    min_value=min_donate,
                    max_value=max_donate,
                    value=default_donate,
                    step=slider_step,
                    key=f"{kp}dq_donate_amount",
                )
            with dc2:
                donate_amount = st.number_input(
                    "Exact",
                    min_value=min_donate,
                    max_value=max_donate,
                    value=donate_amount,
                    step=1,
                    key=f"{kp}dq_donate_exact",
                )

        donate_submitted = st.form_submit_button(
            f"Donate to {target_team if human_teams else '...'}",
            type="primary",
            use_container_width=True,
        )

    if donate_submitted and dtype_keys and donate_amount > 0:
        try:
            resp = api_client.dq_donate(
                session_id, dtype_keys[dtype_idx], donate_amount,
                target_team=target_team,
            )
            st.success(
                f"Donated ${donate_amount:,} to {target_team}! "
                f"Balance: ${resp['bankroll']:,}. Tier: {resp['booster_tier']}"
            )
            st.rerun()
        except api_client.APIError as e:
            st.error(e.detail)


# ---------------------------------------------------------------------------
# History (unchanged API — minor visual tweaks)
# ---------------------------------------------------------------------------

def render_dq_history(session_id: str, key_prefix: str = ""):
    try:
        summary = api_client.dq_summary(session_id)
    except api_client.APIError:
        st.info("DraftyQueenz season history not available yet.")
        return

    weeks = summary.get("weeks", [])
    if not weeks:
        st.info("No completed weeks yet.")
        return

    st.markdown("### Season History")
    mc1, mc2, mc3, mc4 = st.columns(4)
    mc1.metric("Balance", f"${summary.get('bankroll', 0):,}")
    mc2.metric("Total Earned", f"${summary.get('total_earned', 0):,}")
    mc3.metric("Accuracy", f"{summary.get('pick_accuracy', 0):.0f}%")
    mc4.metric("ROI", f"{summary.get('roi', 0):+.1f}%")

    st.markdown("**Week-by-Week Results:**")
    header = "Week | Picks W/L | Pred $ | Fantasy Pts | Fantasy $ | Net"
    divider = "---|---|---|---|---|---"
    rows = [header, divider]
    for w in weeks:
        wk = w.get("week", "?")
        pw = w.get("picks_won", 0)
        pm = w.get("picks_made", 0)
        pred_e = w.get("prediction_earnings", 0)
        fpts = w.get("fantasy_points", 0)
        fan_e = w.get("fantasy_earnings", 0)
        net = pred_e + fan_e
        rows.append(
            f"{wk} | {pw}/{pm} | ${pred_e:,} | {fpts:.1f} | ${fan_e:,} | ${net:,}"
        )
    st.markdown("\n".join(rows))

    clipboard_text = "DraftyQueenz Season Report\n"
    clipboard_text += f"Manager: {summary.get('manager', 'Coach')}\n"
    clipboard_text += (
        f"Balance: ${summary.get('bankroll', 0):,} | "
        f"Earned: ${summary.get('total_earned', 0):,} | "
        f"ROI: {summary.get('roi', 0):+.1f}%\n\n"
    )
    clipboard_text += "Wk  Picks  Pred$    FPts   Fan$    Net\n"
    clipboard_text += "-" * 48 + "\n"
    for w in weeks:
        wk = w.get("week", "?")
        pw = w.get("picks_won", 0)
        pm = w.get("picks_made", 0)
        pred_e = w.get("prediction_earnings", 0)
        fpts = w.get("fantasy_points", 0)
        fan_e = w.get("fantasy_earnings", 0)
        net = pred_e + fan_e
        clipboard_text += (
            f"{wk:<4}{pw}/{pm:<5}${pred_e:<8,}{fpts:<7.1f}"
            f"${fan_e:<7,}${net:,}\n"
        )

    st.text_area(
        "Copy/Paste Export", clipboard_text, height=200,
        key=f"{key_prefix}dq_history_export",
    )


# ---------------------------------------------------------------------------
# Post-sim results (unchanged API)
# ---------------------------------------------------------------------------

def render_dq_post_sim(session_id: str, week: int, key_prefix: str = ""):
    try:
        resolve_resp = api_client.dq_resolve_week(session_id, week)
    except api_client.APIError:
        return

    pred_earn = resolve_resp.get("prediction_earnings", 0)
    fan_earn = resolve_resp.get("fantasy_earnings", 0)
    jackpot = resolve_resp.get("jackpot_bonus", 0)
    total = pred_earn + fan_earn + jackpot
    balance = resolve_resp.get("bankroll", 0)

    if total == 0 and not resolve_resp.get("picks") and not resolve_resp.get("fantasy_rank"):
        return

    with st.expander(f"DraftyQueenz Results — Week {week}", expanded=total > 0):
        rc1, rc2, rc3, rc4 = st.columns(4)
        rc1.metric("Predictions", f"${pred_earn:,}")
        rc2.metric("Fantasy", f"${fan_earn:,}")
        if jackpot > 0:
            rc3.metric("JACKPOT!", f"${jackpot:,}")
        else:
            rc3.metric("Jackpot", "—")
        rc4.metric("Balance", f"${balance:,}")

        picks = resolve_resp.get("picks", [])
        if picks:
            st.markdown("**Prediction Results:**")
            for p in picks:
                icon = (
                    "✓" if p["result"] == "win"
                    else ("—" if p["result"] == "push" else "✗")
                )
                payout_str = (
                    f"+${p['payout']:,}" if p["payout"] > 0 else "$0"
                )
                st.markdown(
                    f"- {icon} {p['pick_type'].title()}: {p['selection']} "
                    f"on {p['matchup']} — {payout_str}"
                )

        parlays = resolve_resp.get("parlays", [])
        if parlays:
            st.markdown("**Parlay Results:**")
            for pl in parlays:
                icon = "✓" if pl["result"] == "win" else "✗"
                payout = pl.get("payout", 0)
                st.markdown(
                    f"- {icon} {len(pl.get('legs', []))}-leg "
                    f"({pl['multiplier']}x) — "
                    f"{'$' + str(payout) if payout else '$0'}"
                )

        fan_rank = resolve_resp.get("fantasy_rank")
        if fan_rank:
            fan_pts = resolve_resp.get("fantasy_points", 0)
            st.markdown(
                f"**Fantasy:** Finished **#{fan_rank}** "
                f"with **{fan_pts:.1f}** pts"
            )
            user_roster = resolve_resp.get("user_roster", {})
            entries = user_roster.get("entries", {})
            if entries:
                for slot, e in entries.items():
                    st.markdown(
                        f"  - {slot}: {e['name']} ({e['team']}) "
                        f"— {e['points']:.1f} pts"
                    )

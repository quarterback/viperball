"""
DraftyQueenz UI components for the Play tab.

Renders pre-sim betting/fantasy and post-sim results inline
within the weekly simulation flow.
"""

import streamlit as st
from ui import api_client


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
    try:
        start_resp = api_client.dq_start_week(session_id, next_week)
    except api_client.APIError as e:
        st.warning(f"DraftyQueenz unavailable: {e.detail}")
        return

    with st.expander(f"DraftyQueenz — Week {next_week}", expanded=False):
        tab_pred, tab_fantasy, tab_donate = st.tabs(["Predictions", "Fantasy", "Donate"])

        with tab_pred:
            _render_predictions_tab(session_id, next_week, key_prefix)

        with tab_fantasy:
            _render_fantasy_tab(session_id, next_week, key_prefix)

        with tab_donate:
            _render_donate_tab(session_id, key_prefix)


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

    st.caption(f"Balance: **${balance:,} DQ$** | Min bet: $250 | Max bet: $25,000")

    try:
        contest_resp = api_client.dq_get_contest(session_id, week)
        existing_picks = contest_resp.get("picks", [])
        existing_parlays = contest_resp.get("parlays", [])
    except api_client.APIError:
        existing_picks = []
        existing_parlays = []

    if existing_picks:
        st.markdown("**Your Picks:**")
        for p in existing_picks:
            result_icon = ""
            if p.get("result") == "win":
                result_icon = " ✓"
            elif p.get("result") == "loss":
                result_icon = " ✗"
            st.markdown(f"- {p['pick_type'].title()}: {p['selection']} on {p['matchup']} — ${p['amount']:,}{result_icon}")

    if existing_parlays:
        st.markdown("**Your Parlays:**")
        for pl in existing_parlays:
            legs_str = ", ".join(f"{l['selection']}" for l in pl.get("legs", []))
            st.markdown(f"- {len(pl.get('legs', []))}-leg ({pl['multiplier']}x): {legs_str} — ${pl['amount']:,}")

    st.divider()
    st.markdown("**Place a Bet**")

    game_labels = [
        f"{o['away_team']} ({o.get('away_ml_display', '')}) @ {o['home_team']} ({o.get('home_ml_display', '')})"
        for o in odds_list
    ]
    game_idx = st.selectbox("Game", range(len(game_labels)),
                             format_func=lambda i: game_labels[i],
                             key=f"{kp}dq_game_select")

    selected_odds = odds_list[game_idx] if game_idx is not None else None

    if selected_odds:
        oc1, oc2, oc3 = st.columns(3)
        oc1.markdown(f"**Spread:** {selected_odds['spread']:+.1f}")
        oc2.markdown(f"**O/U:** {selected_odds['over_under']:.1f}")
        oc3.markdown(f"**KP O/U:** {selected_odds.get('kick_pass_ou', 14.5):.1f}")

    bet_type_labels = {
        "winner": "Winner",
        "spread": "Spread",
        "over_under": "Over/Under",
        "chaos": "Chaos Factor",
        "kick_pass": "Kick Pass O/U",
    }
    pick_type = st.selectbox("Bet Type", list(bet_type_labels.keys()),
                              format_func=lambda x: bet_type_labels.get(x, x),
                              key=f"{kp}dq_pick_type")

    if selected_odds:
        if pick_type in ("winner", "spread"):
            sel_options = [selected_odds["home_team"], selected_odds["away_team"]]
        elif pick_type in ("over_under", "chaos", "kick_pass"):
            sel_options = ["over", "under"]
        else:
            sel_options = ["over", "under"]
        selection = st.selectbox("Pick", sel_options, key=f"{kp}dq_selection")
    else:
        selection = ""

    amount = st.number_input("Wager (DQ$)", min_value=250, max_value=min(25000, balance),
                              value=min(500, balance) if balance >= 250 else 0,
                              step=250, key=f"{kp}dq_bet_amount")

    if st.button("Place Bet", key=f"{kp}dq_place_bet", disabled=balance < 250):
        try:
            resp = api_client.dq_place_pick(session_id, week, pick_type, game_idx, selection, amount)
            st.success(f"Bet placed! Balance: ${resp['bankroll']:,}")
            st.rerun()
        except api_client.APIError as e:
            st.error(e.detail)


def _render_fantasy_tab(session_id: str, week: int, kp: str):
    try:
        roster_resp = api_client.dq_get_roster(session_id, week)
    except api_client.APIError:
        roster_resp = {"entered": False}

    entered = roster_resp.get("entered", False)

    if not entered:
        st.markdown("**Weekly Fantasy** — Entry fee: $2,500 DQ$")
        st.markdown("Draft a 5-player salary-capped roster. Compete against 9 AI managers.")
        if st.button("Enter Fantasy ($2,500)", key=f"{kp}dq_enter_fantasy"):
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

    st.markdown(f"**Your Roster** ({slots_filled}/5 slots) | Salary: ${total_salary:,} / $50,000 | Cap left: ${cap_remaining:,}")

    slot_names = ["VP", "BALL1", "BALL2", "KP", "FLEX"]
    for slot in slot_names:
        entry = entries.get(slot)
        if entry:
            st.markdown(f"- **{slot}**: {entry['name']} ({entry['team']}) [{entry['position']}] — ${entry['salary']:,}")
        else:
            st.markdown(f"- **{slot}**: _(empty)_")

    st.divider()
    st.markdown("**Draft a Player**")

    pos_filter = st.selectbox("Filter by position", ["All", "VP", "HB", "ZB", "WB", "SB", "KP"],
                               key=f"{kp}dq_pos_filter")

    try:
        pool_pos = pos_filter if pos_filter != "All" else None
        pool_resp = api_client.dq_fantasy_pool(session_id, week, position=pool_pos)
        pool = pool_resp.get("pool", [])
    except api_client.APIError:
        pool = []

    if pool:
        player_labels = [
            f"{p['name']} ({p['team']}) [{p['position']}] OVR:{p['overall']} ${p['salary']:,} proj:{p['projected']}"
            for p in pool
        ]
        player_idx = st.selectbox("Player", range(len(player_labels)),
                                    format_func=lambda i: player_labels[i],
                                    key=f"{kp}dq_player_select")

        slot_to_fill = st.selectbox("Slot", slot_names, key=f"{kp}dq_slot_select")

        if st.button("Draft Player", key=f"{kp}dq_draft_player"):
            selected = pool[player_idx]
            try:
                api_client.dq_set_roster_slot(
                    session_id, week, slot_to_fill,
                    selected["tag"], selected["team"]
                )
                st.success(f"Drafted {selected['name']} to {slot_to_fill}!")
                st.rerun()
            except api_client.APIError as e:
                st.error(e.detail)


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

    st.markdown(f"**{tier}** — {tier_desc}")
    st.markdown(f"Career donated: **${career:,} DQ$**")
    if next_tier:
        st.caption(f"Next tier: {next_tier['name']} (${next_tier['amount_needed']:,} to go)")

    human_teams = portfolio.get("human_teams", [])
    team_boosts = portfolio.get("team_boosts", {})

    if team_boosts:
        st.markdown("**Active Boosts by Program:**")
        for team_name, boosts_list in team_boosts.items():
            active = [b for b in boosts_list if b.get("current_value", 0) > 0]
            if active:
                st.markdown(f"**{team_name}**")
                for b in active:
                    pct = b.get("progress_pct", 0)
                    bar_len = 10
                    filled = int(pct / 100 * bar_len)
                    bar = "█" * filled + "░" * (bar_len - filled)
                    st.markdown(f"- {b['label']}: +{b['current_value']:.1f} [{bar}] {pct:.0f}%")
            else:
                st.markdown(f"**{team_name}** — no active boosts yet")
    elif human_teams:
        st.info("No donations made yet. Donate your DQ$ winnings to boost your program!")

    st.divider()
    st.markdown(f"**Make a Donation** (Balance: ${balance:,} | Min: $10,000)")

    if not human_teams:
        st.warning("No coached team found. Start a season or dynasty to donate to a program.")
        return

    target_team = st.selectbox("Donate to Program", human_teams,
                                key=f"{kp}dq_donate_team")

    dtype_options = portfolio.get("donation_types", {})
    if dtype_options:
        dtype_keys = list(dtype_options.keys())
        dtype_labels = [dtype_options[k]["label"] for k in dtype_keys]
        dtype_idx = st.selectbox("Donation Type", range(len(dtype_labels)),
                                   format_func=lambda i: f"{dtype_labels[i]} — {dtype_options[dtype_keys[i]]['description']}",
                                   key=f"{kp}dq_donate_type")

        donate_amount = st.number_input("Amount (DQ$)", min_value=10000,
                                          max_value=max(10000, balance),
                                          value=min(10000, balance) if balance >= 10000 else 10000,
                                          step=5000, key=f"{kp}dq_donate_amount")

        if st.button(f"Donate to {target_team}", key=f"{kp}dq_donate_btn", disabled=balance < 10000):
            try:
                resp = api_client.dq_donate(session_id, dtype_keys[dtype_idx], donate_amount, target_team=target_team)
                st.success(f"Donated ${donate_amount:,} to {target_team}! Balance: ${resp['bankroll']:,}. Tier: {resp['booster_tier']}")
                st.rerun()
            except api_client.APIError as e:
                st.error(e.detail)


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
        rows.append(f"{wk} | {pw}/{pm} | ${pred_e:,} | {fpts:.1f} | ${fan_e:,} | ${net:,}")
    st.markdown("\n".join(rows))

    clipboard_text = "DraftyQueenz Season Report\n"
    clipboard_text += f"Manager: {summary.get('manager', 'Coach')}\n"
    clipboard_text += f"Balance: ${summary.get('bankroll', 0):,} | Earned: ${summary.get('total_earned', 0):,} | ROI: {summary.get('roi', 0):+.1f}%\n\n"
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
        clipboard_text += f"{wk:<4}{pw}/{pm:<5}${pred_e:<8,}{fpts:<7.1f}${fan_e:<7,}${net:,}\n"

    st.text_area("Copy/Paste Export", clipboard_text, height=200,
                   key=f"{key_prefix}dq_history_export")


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
                icon = "✓" if p["result"] == "win" else ("—" if p["result"] == "push" else "✗")
                payout_str = f"+${p['payout']:,}" if p["payout"] > 0 else "$0"
                st.markdown(f"- {icon} {p['pick_type'].title()}: {p['selection']} on {p['matchup']} — {payout_str}")

        parlays = resolve_resp.get("parlays", [])
        if parlays:
            st.markdown("**Parlay Results:**")
            for pl in parlays:
                icon = "✓" if pl["result"] == "win" else "✗"
                st.markdown(f"- {icon} {len(pl.get('legs', []))}-leg ({pl['multiplier']}x) — {'$' + str(pl['payout']) if pl['payout'] else '$0'}")

        fan_rank = resolve_resp.get("fantasy_rank")
        if fan_rank:
            fan_pts = resolve_resp.get("fantasy_points", 0)
            st.markdown(f"**Fantasy:** Finished **#{fan_rank}** with **{fan_pts:.1f}** pts")
            user_roster = resolve_resp.get("user_roster", {})
            entries = user_roster.get("entries", {})
            if entries:
                for slot, e in entries.items():
                    st.markdown(f"  - {slot}: {e['name']} ({e['team']}) — {e['points']:.1f} pts")

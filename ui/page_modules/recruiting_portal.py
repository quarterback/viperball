"""
Recruiting & Transfer Portal Observation Page

Read-only dashboard for watching recruiting and transfers unfold.
Shows HS league results, recruit rankings, signing results, and
autonomous transfer portal activity.
"""

import streamlit as st
import pandas as pd


def render_recruiting_portal(shared):
    """Render the recruiting and portal observation page."""

    st.title("Recruiting & Transfer Portal")

    if "dynasty" not in st.session_state:
        st.info("Start a dynasty to view recruiting and transfer portal activity.")
        return

    dynasty = st.session_state["dynasty"]
    current_year = dynasty.current_year

    tab_hs, tab_recruit, tab_portal, tab_history = st.tabs([
        "HS League", "Recruiting Board", "Transfer Portal", "History",
    ])

    # ══════════════════════════════════════════
    # TAB 1: HS LEAGUE
    # ══════════════════════════════════════════
    with tab_hs:
        st.subheader("High School League")

        if dynasty._hs_league is None:
            st.caption("HS league will be simulated during the next offseason advance.")
            return

        from engine.hs_league import league_summary
        league = dynasty._hs_league
        summary = league_summary(league)

        col1, col2, col3, col4 = st.columns(4)
        col1.metric("Teams", summary["total_teams"])
        col2.metric("States", summary["states"])
        col3.metric("Seniors", summary["graduating_seniors"])
        col4.metric("Games", summary["games_played"])

        if summary["national_champion"]:
            st.success(f"**National Champion:** {summary['national_champion']}")

        # Region champions
        st.subheader("Regional Champions")
        if summary["region_champions"]:
            region_data = [
                {"Region": r, "Champion": c}
                for r, c in sorted(summary["region_champions"].items())
            ]
            st.dataframe(pd.DataFrame(region_data), use_container_width=True, hide_index=True)

        # State champions
        with st.expander("State Champions", expanded=False):
            if summary["state_champions"]:
                from engine.hs_league_data import STATES
                state_data = []
                for code, champ in sorted(summary["state_champions"].items()):
                    state_name = STATES.get(code, {}).get("name", code)
                    state_data.append({"State": state_name, "Code": code, "Champion": champ})
                st.dataframe(pd.DataFrame(state_data), use_container_width=True, hide_index=True)

        # Top HS teams by record
        with st.expander("Top HS Teams by Record", expanded=False):
            all_teams = sorted(league.teams.values(), key=lambda t: (-t.wins, -t.points_for))
            top_data = []
            for t in all_teams[:30]:
                from engine.hs_league_data import STATES
                state_name = STATES.get(t.state, {}).get("name", t.state)
                badges = []
                if t.national_champ:
                    badges.append("NAT")
                if t.region_champ:
                    badges.append("REG")
                if t.state_champ:
                    badges.append("ST")
                if t.conf_champ:
                    badges.append("CONF")
                top_data.append({
                    "School": t.school_name,
                    "State": state_name,
                    "Conference": t.conference,
                    "Record": t.record,
                    "PF": round(t.points_for, 1),
                    "PA": round(t.points_against, 1),
                    "Titles": " ".join(badges) if badges else "",
                })
            st.dataframe(pd.DataFrame(top_data), use_container_width=True, hide_index=True)

        # Browse by state
        with st.expander("Browse by State", expanded=False):
            from engine.hs_league_data import STATES
            state_options = sorted(STATES.keys())
            selected_state = st.selectbox(
                "Select State",
                state_options,
                format_func=lambda s: f"{STATES[s]['name']} ({s})",
                key="hs_browse_state",
            )
            if selected_state:
                state_teams = league.get_teams_by_state(selected_state)
                state_teams.sort(key=lambda t: (-t.wins, t.school_name))
                state_data = []
                for t in state_teams:
                    badges = []
                    if t.state_champ:
                        badges.append("STATE CHAMP")
                    if t.conf_champ:
                        badges.append("CONF CHAMP")
                    state_data.append({
                        "School": t.school_name,
                        "Conference": t.conference,
                        "Record": t.record,
                        "Strength": round(t.strength, 1),
                        "Seniors": len(t.seniors),
                        "Title": " | ".join(badges) if badges else "",
                    })
                st.dataframe(pd.DataFrame(state_data), use_container_width=True, hide_index=True)

    # ══════════════════════════════════════════
    # TAB 2: RECRUITING BOARD
    # ══════════════════════════════════════════
    with tab_recruit:
        st.subheader("Recruiting Board")

        rec_history = dynasty.recruiting_history.get(current_year)
        if not rec_history:
            st.caption("No recruiting data yet. Advance the season to see results.")
        else:
            col1, col2, col3 = st.columns(3)
            col1.metric("Pool Size", rec_history.get("pool_size", "?"))
            hs_champ = rec_history.get("hs_national_champion", "")
            if hs_champ:
                col2.metric("HS National Champ", hs_champ)
            total_signed = sum(rec_history.get("signed_count", {}).values())
            col3.metric("Players Signed", total_signed)

            # Class rankings
            st.subheader("Recruiting Class Rankings")
            rankings = rec_history.get("class_rankings", [])
            if rankings:
                rank_data = []
                for i, (team, avg_stars, count) in enumerate(rankings[:30]):
                    rank_data.append({
                        "Rank": i + 1,
                        "School": team,
                        "Avg Stars": f"{avg_stars:.1f}",
                        "Signees": count,
                        "Prestige": dynasty.team_prestige.get(team, 50),
                    })
                st.dataframe(pd.DataFrame(rank_data), use_container_width=True, hide_index=True)

            # HS State champions for this class
            hs_state_champs = rec_history.get("hs_state_champions", {})
            if hs_state_champs:
                with st.expander("HS State Champions (this class)", expanded=False):
                    from engine.hs_league_data import STATES
                    champ_data = [
                        {"State": STATES.get(c, {}).get("name", c), "Champion": ch}
                        for c, ch in sorted(hs_state_champs.items())
                    ]
                    st.dataframe(pd.DataFrame(champ_data), use_container_width=True, hide_index=True)

    # ══════════════════════════════════════════
    # TAB 3: TRANSFER PORTAL
    # ══════════════════════════════════════════
    with tab_portal:
        st.subheader("Transfer Portal")

        portal_history = dynasty.portal_history.get(current_year - 1)
        if not portal_history:
            # Try current year
            portal_history = dynasty.portal_history.get(current_year)

        if not portal_history:
            st.caption("No transfer portal activity yet. Advance the season to see results.")
        else:
            transfers = portal_history.get("transfers", [])
            total_entries = portal_history.get("total_entries", 0)

            col1, col2 = st.columns(2)
            col1.metric("Portal Entries", total_entries)
            col2.metric("Transfers Completed", len(transfers))

            if transfers:
                st.subheader("Completed Transfers")
                xfer_data = []
                for t in transfers:
                    xfer_data.append({
                        "Player": t.get("player", "?"),
                        "Position": t.get("position", "?"),
                        "Overall": t.get("overall", "?"),
                        "From": t.get("from", "?"),
                        "To": t.get("to", "?"),
                    })
                df = pd.DataFrame(xfer_data)
                # Sort by overall descending
                if not df.empty and "Overall" in df.columns:
                    df = df.sort_values("Overall", ascending=False)
                st.dataframe(df, use_container_width=True, hide_index=True)

    # ══════════════════════════════════════════
    # TAB 4: HISTORY
    # ══════════════════════════════════════════
    with tab_history:
        st.subheader("Recruiting History")

        years = sorted(dynasty.recruiting_history.keys(), reverse=True)
        if not years:
            st.caption("No recruiting history yet.")
        else:
            for yr in years:
                rh = dynasty.recruiting_history[yr]
                with st.expander(f"Class of {yr}", expanded=(yr == current_year)):
                    col1, col2, col3 = st.columns(3)
                    col1.metric("Pool Size", rh.get("pool_size", "?"))
                    total = sum(rh.get("signed_count", {}).values())
                    col2.metric("Total Signed", total)
                    hs_champ = rh.get("hs_national_champion", "")
                    if hs_champ:
                        col3.metric("HS Nat'l Champ", hs_champ)

                    # Top recruiting classes
                    rankings = rh.get("class_rankings", [])
                    if rankings:
                        rank_data = [
                            {"Rank": i + 1, "School": t, "Avg Stars": f"{s:.1f}", "Signees": c}
                            for i, (t, s, c) in enumerate(rankings[:10])
                        ]
                        st.dataframe(pd.DataFrame(rank_data), use_container_width=True, hide_index=True)

        st.divider()
        st.subheader("Transfer Portal History")
        portal_years = sorted(dynasty.portal_history.keys(), reverse=True)
        if not portal_years:
            st.caption("No portal history yet.")
        else:
            for yr in portal_years:
                ph = dynasty.portal_history[yr]
                transfers = ph.get("transfers", [])
                with st.expander(f"{yr} Portal ({len(transfers)} transfers)", expanded=False):
                    if transfers:
                        xfer_data = [
                            {"Player": t["player"], "Pos": t.get("position", "?"),
                             "OVR": t.get("overall", "?"), "From": t["from"], "To": t["to"]}
                            for t in transfers
                        ]
                        st.dataframe(pd.DataFrame(xfer_data), use_container_width=True, hide_index=True)
                    else:
                        st.caption("No transfers this year.")

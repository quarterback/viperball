"""Weekly regional rankings; independent of conference membership."""

REGIONS = {
    "New England": "CT ME MA NH RI VT",
    "Mid-Atlantic": "NY NJ PA DE MD DC VA WV",
    "Southeast": "NC SC GA FL AL MS TN KY",
    "Great Lakes": "OH MI IN IL WI",
    "Central": "MN IA MO ND SD NE KS",
    "South Central": "TX OK AR LA",
    "Mountain": "MT ID WY CO UT NV AZ NM",
    "Pacific": "WA OR CA AK HI",
}
STATE_REGION = {state: region for region, states in REGIONS.items()
                for state in states.split()}


def build_regional_polls(week, team_states, standings, schedule,
                         power_rankings, previous, national_ranks, history=()):
    """Blend national resume (60%) with regional results (40%).

    No invented ballots. Unmapped schools remain nationally eligible.
    Only completed games through the requested week count.
    """
    membership = {name: STATE_REGION.get(str(state).strip().upper())
                  for name, state in team_states.items()}
    power = {name: (score, qw) for name, score, qw in power_rankings}
    results = {}
    historical = {p.week: getattr(p, 'regional_rankings', {}) for p in history}
    for region in REGIONS:
        members = {name for name in power if membership.get(name) == region}
        if not members:
            continue
        prior = {row["team_name"]: row["rank"]
                 for row in previous.get(region, [])}
        records = {name: [0, 0, 0, 0] for name in members}
        for game in schedule:
            if not game.completed or game.week > week or game.is_fcs_game:
                continue
            if game.home_score is None or game.away_score is None:
                continue
            for name, opp, score, against in (
                (game.home_team, game.away_team, game.home_score, game.away_score),
                (game.away_team, game.home_team, game.away_score, game.home_score),
            ):
                if name not in members or membership.get(opp) != region:
                    continue
                rec = records[name]
                rec[0 if score > against else 1 if score < against else 2] += 1
                earlier = [w for w in historical if w < game.week]
                ranked = historical[max(earlier)].get(region, []) if earlier else []
                if score > against and any(row['team_name'] == opp for row in ranked):
                    rec[3] += 1
        rows = []
        for name in sorted(members):
            w, l, t, ranked_wins = records[name]
            games = w + l + t
            regional_pct = (w + .5 * t) / games if games else .5
            # Shrink small regional samples toward neutral.
            regional_pct = (regional_pct * games + 1) / (games + 2)
            pi, qw = power[name]
            score = .6 * pi + 35 * regional_pct + min(5, ranked_wins * 2.5)
            rows.append(dict(team_name=name, record=standings[name].record_str,
                             conference=standings[name].conference,
                             regional_record=f"{w}-{l}" + (f"-{t}" if t else ""),
                             regional_quality_wins=ranked_wins,
                             national_rank=national_ranks.get(name),
                             power_index=pi, poll_score=round(score, 2),
                             prev_rank=prior.get(name)))
        rows.sort(key=lambda row: (-row["poll_score"], -row["power_index"], row["team_name"]))
        for rank, row in enumerate(rows[:10], 1):
            row["rank"] = rank
            row["rank_change"] = None if row["prev_rank"] is None else row["prev_rank"] - rank
        results[region] = rows[:10]
    return results

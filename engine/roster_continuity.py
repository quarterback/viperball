"""Restore finalized offseason rosters without silent player loss."""
from engine.player_card import PlayerCard, card_to_player


def restore_finalized_rosters(teams, saved_rosters):
    """Validate and convert all known program rosters before replacing any.

    Missing keys are allowed for new programs. Existing saved identities
    are preserved, including legacy IDs; this function does not rewrite
    career history or silently deduplicate players.
    """
    restored = {}
    for name in teams:
        if name not in saved_rosters:
            continue
        rows = saved_rosters[name]
        if not isinstance(rows, list) or not rows:
            raise ValueError(f"Finalized roster for {name} is empty or invalid")
        players = []
        for index, row in enumerate(rows):
            try:
                if not isinstance(row, dict):
                    raise TypeError("Expected player record")
                card = PlayerCard.from_dict(row)
                if not card.first_name or not card.last_name or not card.position:
                    raise ValueError("Player name or position missing")
                players.append(card_to_player(card))
            except Exception as exc:
                raise ValueError(
                    f"Finalized roster for {name}: cannot restore player record {index + 1}: {exc}"
                ) from exc
        restored[name] = players
    for name, players in restored.items():
        teams[name].players = players


def retired_dispersal_sources(retired_programs, pending_programs, saved_rosters):
    """Only disperse a retired program that has an actual saved roster or
    a newly recorded retirement awaiting its first season boundary.
    A roster generated from a program file on every start is not a new
    pool of free agents from a previously frozen program.
    """
    return sorted(set(retired_programs) &
                  (set(pending_programs) | set(saved_rosters or {})))


# Same position mix as the existing college roster template, not a new
# talent or performance target. Existing larger rosters are not cut.
COLLEGE_DEPTH = {"Viper": 3, "Zeroback": 3, "Halfback": 4, "Wingback": 4,
                 "Slotback": 4, "Keeper": 3, "Offensive Line": 8,
                 "Defensive Line": 7}
COLLEGE_ROSTER_TARGET = sum(COLLEGE_DEPTH.values())


def projected_rosters(cards_by_team, portal):
    """Return continuing cards after committed eligible transfers.
    Use stable identity, not display name. Do not mutate input cards.
    """
    from copy import deepcopy
    result = {t: [deepcopy(c) for c in cards if c.year != "Graduate"]
              for t, cards in cards_by_team.items()}
    for entry in getattr(portal, "entries", ()):
        src, dst = entry.origin_team, entry.committed_to
        if not dst or src == dst or src not in result or dst not in result:
            continue
        pid = entry.player_card.player_id
        if not pid:
            raise ValueError("Transfer missing stable player ID")
        found = [c for c in result[src] if c.player_id == pid]
        if len(found) != 1:
            raise ValueError(f"Transfer source must contain exactly one eligible player: {pid}")
        card = found[0]
        result[src].remove(card)
        card.transfer_count += 1
        card.current_team = dst
        result[dst].append(card)
    return result


def fill_college_roster_gaps(rosters, recruit_pool, year, rng, unavailable_ids=(), reserve_pool=()):
    """Use unsigned prospects for depth, then explicit emergency walk-ons.
    Never cut signed or returning players to meet the ordinary roster target.
    """
    from collections import Counter
    from engine.recruiting import generate_single_recruit
    used = {c.player_id for cards in rosters.values() for c in cards}
    used.update(unavailable_ids)
    candidates = [r for r in recruit_pool if not r.signed and not r.committed_to
                  and r.recruit_id not in used]
    rng.shuffle(candidates)
    reserves = [r for r in reserve_pool if not r.signed and not r.committed_to and r.recruit_id not in used]
    rng.shuffle(reserves)
    by_team = {}
    fallback = 0
    # Rotate which school gets first pick; no alphabetical recruiting advantage.
    teams = sorted(rosters)
    rng.shuffle(teams)
    while any(len(rosters[t]) < COLLEGE_ROSTER_TARGET for t in teams):
        for team in teams:
            roster = rosters[team]
            if len(roster) >= COLLEGE_ROSTER_TARGET:
                continue
            counts = Counter(c.position for c in roster)
            pos = max(COLLEGE_DEPTH, key=lambda p: COLLEGE_DEPTH[p] - counts[p])
            idx = next((i for i, r in enumerate(candidates)
                        if r.position == pos and r.recruit_id not in used), None)
            reserve_idx = (next((i for i,r in enumerate(reserves)
                                if r.position == pos and r.recruit_id not in used),None)
                           if idx is None else None)
            if reserve_idx is not None:
                recruit = reserves.pop(reserve_idx)
                source = "hs_reserve"
            elif idx is None:
                fallback += 1
                rid = f"WALKON-{year}-{fallback:05d}"
                while rid in used:
                    fallback += 1
                    rid = f"WALKON-{year}-{fallback:05d}"
                recruit = generate_single_recruit(rid, position=pos, rng=rng)
                source = "emergency"
            else:
                recruit = candidates.pop(idx)
                source = "unsigned"
            recruit.committed_to = team
            recruit.signed = True
            recruit.is_walkon = True
            recruit.signing_phase = "walkon"
            roster.append(recruit.to_player_card(team))
            used.add(recruit.recruit_id)
            by_team.setdefault(team, []).append({"player_id": recruit.recruit_id,
                "position": pos, "source": source, "overall": roster[-1].overall})
    # Preserve existing numbers where possible; assign unnumbered recruits
    # and resolve collisions after transfers.
    for team, roster in rosters.items():
        numbers = set()
        for card in roster:
            if card.number not in range(1, 100) or card.number in numbers:
                card.number = next((n for n in range(1, 100) if n not in numbers), 0)
            numbers.add(card.number)
    return by_team


def assign_opening_roster_ids(teams, saved_rosters, year):
    """Namespace new college players by program, entry season and slot.

    Fresh generator name/suffix IDs can collide across schools. Never
    change a finalized saved roster's IDs or use names as identity.
    """
    import hashlib
    used = {row.get("player_id") for rows in saved_rosters.values() for row in rows}
    for name, team in sorted(teams.items()):
        if name in saved_rosters:
            continue
        for i, player in enumerate(team.players):
            digest = hashlib.sha256(f"{name}:{year}:{i}".encode()).hexdigest()[:24]
            pid = f"CVL-OPEN-{year}-{digest}"
            if pid in used:
                raise ValueError(f"Opening college player identity already exists: {pid}")
            player.player_id = pid
            used.add(pid)

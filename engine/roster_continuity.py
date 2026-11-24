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

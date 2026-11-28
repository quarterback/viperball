"""Play designs that carry a decision through execution."""

KICK_AND_FOLLOW = "gaelic_kick_and_follow"
BOUNDARY_SWITCH = "afl_boundary_switch"
CARRY_RELEASE = "rugby_carry_release"
PROTECT_BONUS = "ball_protect_bonus"
CORNER_CHASE = "cfl_corner_chase"

SEQUENCES = {BOUNDARY_SWITCH, CARRY_RELEASE}


def sequence_call(package_id, setup):
    """Choose the next leg from completed calls on the current possession."""
    lane = setup[-1]["lane"] if setup else ("left" if package_id == BOUNDARY_SWITCH else "right")
    # Allow a defense that preserves its width to keep the ball on that side.
    # Once the defense presses the setup, split the attack to the other side.
    if len(setup) >= 2 and setup[-1]["pressed"]:
        lane = "left" if lane == "right" else "right"
        if package_id == BOUNDARY_SWITCH:
            return {"phase": "switch", "lane": lane, "family": "kick_pass", "kick_pass": "territory"}
        return {"phase": "release", "lane": lane, "family": "sweep_option"}
    if package_id == BOUNDARY_SWITCH:
        return {"phase": "setup", "lane": lane, "family": "kick_pass", "kick_pass": "quick_kick"}
    return {"phase": "setup", "lane": lane, "family": "power"}


def follow_read(receiver, support, defender):
    """Give it to a fresher support runner when the catch is under pressure."""
    if support is None or defender is None:
        return False
    runner = lambda player: (player.speed + player.agility) / 2 * (0.5 + player.game_energy / 200)
    # Closing speed gives the defender a chance to stop the receiver and the
    # lateral still has to survive the existing fumble and interception rolls.
    return (defender.speed + defender.tackling) / 2 >= runner(receiver) and runner(support) >= runner(receiver)

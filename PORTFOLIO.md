# Viperball

A fictional sport developed into a playable simulation universe. Viperball grew from a question about pre-forward-pass football: how would a modern sport develop around running, kicking, lateral movement and two-way players?

## The sport
A 100-yard field, six downs for 20 yards, 11 players on the field, no thrown forward pass. Six ways to score, from nine-point touchdowns to half-point bells. Delta restarts and interception-generated bonus possessions create a distinctive possession game. The full rulebook defines the sport.

## The simulation
A Python engine resolves contests among actual players, with 16 offensive schools, 10 defensive schools, five special-teams schemes and situational packages. It tracks weather, injuries, officiating, fatigue, shifts and real defensive commitments. The college dynasty models recruiting cohorts, staff careers, retirement, development and program continuity.

## The world
Women's college programs, high-school feeder competition, professional leagues, WVL's multi-tier club system, and international FIV competition. New college recruiting cohorts come from actual high-school players rather than a disconnected prospect generator.

## The interface
The main browser interface combines live league management and a reference-style statistical site. Game reports reconcile all scoring channels, link to individual players and coaches, and provide full play-by-play and drive records. The analytics portal offers leaderboards, situational search, heatmaps, comparison and export, drawing on Baseball Savant, FanGraphs and Pro Football Reference. Experimental models are explicitly separated from observed statistics.

## Engineering practice
The application is a single Python process with FastAPI, Jinja2, NiceGUI and SQLite. Development uses seeded simulations, integration tests, national and longitudinal benchmarks, and dated after-action reports. Model calibration and live deployment verification are independent from implementation and merge status.

See [README](README.md), [documentation index](docs/README.md) and [development plan](docs/DEVELOPMENT_PLAN.md). Hosted build status should be checked before sharing live links or screenshots.

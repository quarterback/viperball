# Retiring the /app React workbench

The stats site (`/stats`, viperball.xyz) becomes the only interface. Its pages
gain the controls the workbench had, as plain HTML forms that call the same
API functions in `api/main.py` and redirect back. The `web/` folder, the Node
stage in the Dockerfile and the `/app` mount are deleted only when every row
below is checked.

## Parity checklist

### College season (phase 1)
- [x] New season: name, up to 4 human teams, playoff size, bowl count, history years, AI seed
- [x] Sim week, sim rest of season
- [x] Bowls, playoffs
- [x] Skip transfer portal
- [x] New season: per team offense, defense and special teams styles
- [x] New season: conference alignment editor
- [x] In-season portal: commit a player to a team
- [x] Player edit, player add, player move, team rename and team details
- [ ] Archive a finished season (stats site has a fetch button already; move to a form)

### Saves
- [x] One list of every save (`/api/saves`): open, fork, rename, tag, delete

### Dynasty
- [x] Create dynasty, start season, advance
- [x] Programs: add, retire, restore
- [x] Offseason: NIL allocation, portal offer/commit/resolve, recruiting scout/offer/assign/resolve, recruit editor, complete

### My Team
- [x] Already on the stats site (retention lock, portal bid/advance, sim, run it back)
- [ ] Finalize (check against `/sessions/{sid}/my-team/finalize`)

### Pro leagues
- [ ] Start a league, sim week, sim all

### WVL
- [ ] Create, sim week, sim all, advance season, import graduates

### International (FIV)
- [ ] New cycle, sim stage, continental sim all

### Other workbench pages
- [ ] Game Sim (single game)
- [ ] Compare runs
- [ ] DraftyQueenz picks and parlays
- [ ] Export

### Removal
- [ ] Delete `web/`, the Node stage in `Dockerfile`, the `/app` mount in `api/main.py`
- [ ] Redirect `/app/*` to `/stats/`

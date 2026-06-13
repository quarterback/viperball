import { createBrowserRouter } from "react-router-dom";
import { AppLayout } from "../components/AppLayout";
import { SavesLibrary } from "../pages/SavesLibrary";
import { Placeholder } from "../pages/Placeholder";

// Real, deep-linkable URLs — the #1 fix over the old single-"/" NiceGUI app.
// basename matches Vite's base ("/app") so prod + dev routing line up.
export const router = createBrowserRouter(
  [
    {
      path: "/",
      element: <AppLayout />,
      children: [
        { index: true, element: <SavesLibrary /> },
        {
          path: "league",
          element: (
            <Placeholder
              title="College Season — League Hub"
              phase="Phase 2"
              blurb="The flagship. Dense standings/schedule/polls/leaders grids with instant drill-down to team and player pages, each on its own URL."
              endpoints={[
                "GET /sessions/{id}/season/standings",
                "GET /sessions/{id}/season/schedule",
                "GET /sessions/{id}/season/polls",
                "GET /sessions/{id}/season/player-stats",
                "GET /sessions/{id}/team/{team}",
                "POST /sessions/{id}/season/simulate-week",
              ]}
            />
          ),
        },
        {
          path: "compare",
          element: (
            <Placeholder
              title="Compare Runs"
              phase="Phase 3"
              blurb="Side-by-side diff of two or more saves — the experiment payoff. Compare final standings, champions, stat leaders, and DTW/luck across runs."
              endpoints={[
                "GET /api/saves",
                "GET /sessions/{id}/season/standings",
                "GET /sessions/{id}/season/awards",
                "GET /sessions/{id}/season/dtw",
              ]}
            />
          ),
        },
        {
          path: "team",
          element: (
            <Placeholder
              title="My Team"
              phase="Phase 4"
              blurb="Roster, chemistry, retention/portal — the single-team management view."
              endpoints={[
                "GET /sessions/{id}/my-team",
                "GET /sessions/{id}/teams/{team}/chemistry",
                "GET /sessions/{id}/my-team/portal",
              ]}
            />
          ),
        },
        {
          path: "pro",
          element: (
            <Placeholder
              title="Pro Leagues"
              phase="Phase 4"
              blurb="Pro season standings, schedule, playoffs, stat leaders."
              endpoints={[
                "GET /api/pro/{league}/{id}/standings",
                "GET /api/pro/{league}/{id}/schedule",
                "POST /api/pro/{league}/{id}/sim-week",
              ]}
            />
          ),
        },
        {
          path: "international",
          element: (
            <Placeholder
              title="International (FIV)"
              phase="Phase 4"
              blurb="Confederations, World Cup, world rankings."
              endpoints={[
                "GET /api/fiv/rankings",
                "GET /api/fiv/worldcup/groups",
                "GET /api/fiv/worldcup/bracket",
              ]}
            />
          ),
        },
        {
          path: "export",
          element: (
            <Placeholder
              title="Export"
              phase="Phase 2"
              blurb="One-click export of standings, box scores, and history in the formats already generated."
              endpoints={[
                "POST /archives/college/{id}",
                "GET /archives",
                "GET /stats/export/college/{id}/standings.json",
              ]}
            />
          ),
        },
      ],
    },
  ],
  { basename: "/app" },
);

import { createBrowserRouter } from "react-router-dom";
import { AppLayout } from "../components/AppLayout";
import { SavesLibrary } from "../pages/SavesLibrary";
import { LeagueIndex } from "../pages/league/LeagueIndex";
import { NewSeason } from "../pages/league/NewSeason";
import { LeagueHub } from "../pages/league/LeagueHub";
import { TeamPage } from "../pages/league/TeamPage";
import { PlayerPage } from "../pages/league/PlayerPage";
import { ArchiveView } from "../pages/league/ArchiveView";
import { GameBoxScore } from "../pages/league/GameBoxScore";
import { Compare } from "../pages/Compare";
import { ProIndex } from "../pages/pro/ProIndex";
import { ProHub } from "../pages/pro/ProHub";
import { International } from "../pages/International";
import { DynastyIndex } from "../pages/dynasty/DynastyIndex";
import { DynastyCreate } from "../pages/dynasty/DynastyCreate";
import { DynastyHub } from "../pages/dynasty/DynastyHub";
import { MyTeam } from "../pages/MyTeam";
import { Export } from "../pages/Export";

// Real, deep-linkable URLs — the #1 fix over the old single-"/" NiceGUI app.
// basename matches Vite's base ("/app") so prod + dev routing line up.
export const router = createBrowserRouter(
  [
    {
      path: "/",
      element: <AppLayout />,
      children: [
        { index: true, element: <SavesLibrary /> },
        { path: "league", element: <LeagueIndex /> },
        { path: "league/new", element: <NewSeason /> },
        { path: "league/archive/:archiveKey", element: <ArchiveView /> },
        { path: "league/:sessionId", element: <LeagueHub /> },
        { path: "league/:sessionId/game/:week/:away/:home", element: <GameBoxScore /> },
        { path: "league/:sessionId/team/:teamName", element: <TeamPage /> },
        {
          path: "league/:sessionId/team/:teamName/player/:playerName",
          element: <PlayerPage />,
        },
        { path: "compare", element: <Compare /> },
        { path: "dynasty", element: <DynastyIndex /> },
        { path: "dynasty/new", element: <DynastyCreate /> },
        { path: "dynasty/:sessionId", element: <DynastyHub /> },
        { path: "team", element: <MyTeam /> },
        { path: "pro", element: <ProIndex /> },
        { path: "pro/:league/:sessionId", element: <ProHub /> },
        { path: "international", element: <International /> },
        { path: "export", element: <Export /> },
      ],
    },
  ],
  { basename: "/app" },
);

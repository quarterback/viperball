import { Spotlight, type SpotlightActionData } from "@mantine/spotlight";
import { IconSearch, IconLayoutGrid, IconTrophy, IconChartBar, IconUsers } from "@tabler/icons-react";
import { useNavigate } from "react-router-dom";

// Linear/Notion-style command palette. Phase 1 ships navigation actions;
// later we feed it teams/players/games from the active save for instant jump-to.
export function CommandPalette() {
  const navigate = useNavigate();

  const actions: SpotlightActionData[] = [
    {
      id: "saves",
      label: "Saves Library",
      description: "All your experiments",
      onClick: () => navigate("/"),
      leftSection: <IconLayoutGrid size={18} />,
    },
    {
      id: "league",
      label: "League Hub",
      description: "Standings, schedule, leaders",
      onClick: () => navigate("/league"),
      leftSection: <IconTrophy size={18} />,
    },
    {
      id: "compare",
      label: "Compare Runs",
      description: "Diff experiments side by side",
      onClick: () => navigate("/compare"),
      leftSection: <IconChartBar size={18} />,
    },
    {
      id: "team",
      label: "My Team",
      onClick: () => navigate("/team"),
      leftSection: <IconUsers size={18} />,
    },
  ];

  return (
    <Spotlight
      actions={actions}
      nothingFound="Nothing found…"
      highlightQuery
      searchProps={{
        leftSection: <IconSearch size={18} />,
        placeholder: "Jump to a screen, team, or player…",
      }}
    />
  );
}

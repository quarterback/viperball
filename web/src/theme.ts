import { createTheme, type MantineColorsTuple } from "@mantine/core";

// Brand indigo carried over from the old app's --vb-accent (#818cf8 family),
// authored natively for a LIGHT theme this time — no dark-class overrides.
const indigo: MantineColorsTuple = [
  "#eef0ff",
  "#dadefb",
  "#b1b9f1",
  "#8590e9",
  "#616fe1",
  "#4a5bdd",
  "#3e51dc",
  "#3042c4",
  "#2a3bb0",
  "#21319b",
];

export const theme = createTheme({
  primaryColor: "indigo",
  primaryShade: { light: 6 },
  colors: { indigo },
  fontFamily:
    "Inter, -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif",
  headings: { fontWeight: "700" },
  defaultRadius: "md",
  cursorType: "pointer",
  components: {
    Card: { defaultProps: { withBorder: true, shadow: "xs" } },
    Button: { defaultProps: { variant: "light" } },
  },
});

// Semantic colors for sim data (win/loss, scoring, luck) — used across grids.
export const semantic = {
  win: "teal",
  loss: "red",
  td: "teal",
  turnover: "red",
  hot: "orange",
  cold: "blue",
  neutral: "gray",
} as const;

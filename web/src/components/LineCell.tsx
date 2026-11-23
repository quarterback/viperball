import { Badge, Group, Text, Tooltip } from "@mantine/core";

/** Midfield line (1 to 3) for Vipers and flankers, with a DS badge for the
 *  defensive specialist. Other positions show nothing. */
export function LineCell({ line, specialist }: { line?: number | null; specialist?: boolean }) {
  if (!line) return null;
  return (
    <Group gap={4} wrap="nowrap">
      <Text size="sm">{line}</Text>
      {specialist && (
        <Tooltip label="Defensive specialist: comes on for defensive possessions">
          <Badge size="xs" variant="light" color="grape">
            DS
          </Badge>
        </Tooltip>
      )}
    </Group>
  );
}

export const LINE_HEADER_TITLE =
  "Midfield line: the Viper and four flankers play together and change as a unit";

import { useQuery, useMutation } from "@tanstack/react-query";
import { useNavigate } from "react-router-dom";
import {
  Stack,
  Group,
  Title,
  Text,
  Card,
  Badge,
  SimpleGrid,
  Loader,
  Center,
} from "@mantine/core";
import { IconCrown, IconChevronRight } from "@tabler/icons-react";
import { notifications } from "@mantine/notifications";
import { dynastyApi } from "../../api/dynasty";

export function DynastyIndex() {
  const navigate = useNavigate();
  const { data, isLoading } = useQuery({
    queryKey: ["dynasties"],
    queryFn: dynastyApi.list,
  });

  const open = useMutation({
    mutationFn: (saveKey: string) => dynastyApi.open(saveKey),
    onSuccess: (sid) => navigate(`/dynasty/${sid}`),
    onError: () => notifications.show({ message: "Couldn't load dynasty", color: "red" }),
  });

  return (
    <Stack gap="md">
      <Stack gap={2}>
        <Title order={2}>Dynasties</Title>
        <Text c="dimmed" size="sm">
          Saved multi-year careers. Open one to browse its history, records, and awards.
        </Text>
      </Stack>

      {isLoading && (
        <Center py="xl">
          <Loader />
        </Center>
      )}

      {data && data.length === 0 && (
        <Card>
          <Text c="dimmed">
            No saved dynasties yet. Start one in the legacy app — the dynasty creation flow is on
            the rebuild list.
          </Text>
        </Card>
      )}

      {data && data.length > 0 && (
        <SimpleGrid cols={{ base: 1, sm: 2, lg: 3 }}>
          {data.map((d) => (
            <Card
              key={d.save_key}
              padding="md"
              onClick={() => open.mutate(d.save_key)}
              style={{ cursor: "pointer", opacity: open.isPending ? 0.6 : 1 }}
            >
              <Group justify="space-between" mb="xs" wrap="nowrap">
                <Group gap="xs" wrap="nowrap">
                  <IconCrown size={18} color="var(--mantine-color-grape-6)" />
                  <Text fw={600} lineClamp={1}>
                    {d.dynasty_name}
                  </Text>
                </Group>
                <IconChevronRight size={16} color="var(--mantine-color-gray-5)" />
              </Group>
              <Group gap="xs">
                <Badge variant="light" color="grape" radius="sm">
                  {d.coach_team}
                </Badge>
                <Badge variant="light" color="gray" radius="sm">
                  Year {d.current_year}
                </Badge>
                <Badge variant="light" color="gray" radius="sm">
                  {d.seasons_played} seasons
                </Badge>
              </Group>
              <Text size="xs" c="dimmed" mt="sm">
                {d.coach_name}
              </Text>
            </Card>
          ))}
        </SimpleGrid>
      )}
    </Stack>
  );
}

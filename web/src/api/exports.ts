// Export / archive API.
import { apiGet, apiSend } from "./client";

export interface ArchiveMeta {
  save_key: string;
  label: string;
  created_at: number;
  updated_at: number;
  data_size: number;
}

export const exportApi = {
  archives: () =>
    apiGet<{ archives: ArchiveMeta[] }>("/archives").then((r) => r.archives),
  archiveSeason: (sid: string) => apiSend("POST", `/archives/college/${sid}`),
};

// Direct download URLs (served by the stats sub-app / archive store).
export const standingsJsonUrl = (sid: string) =>
  `/stats/export/college/${sid}/standings.json`;
export const archiveJsonUrl = (key: string) => `/archives/${encodeURIComponent(key)}`;

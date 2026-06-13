// Standalone Recruiting — scan the incoming HS recruit class for a dynasty
// before the offseason (read-only board).
import { apiGet } from "./client";

export interface ProspectRow {
  recruit_id: string;
  rank: number;
  name: string;
  position: string;
  scouted_stars: number;
  grade: string;
  hometown: string;
  high_school: string;
  region: string;
  height: string;
  weight: number;
  position_rank: number;
  regional_rank: number;
  is_alpha: boolean;
  visible_attributes: Record<string, number>;
  gpa: number;
  sat_score: number;
  field_intelligence: number;
  coachability: number;
  academic_risk: string;
  flag?: string;
}

export interface GradeSummary {
  count: number;
  avg_scouted_stars?: number;
  five_star?: number;
  four_star?: number;
  alpha_count?: number;
  sleeper_count?: number;
}

export interface PipelineResponse {
  dynasty_name: string;
  year: number | null;
  summary: Record<string, GradeSummary>;
  grade: string;
  grades: string[];
  board: ProspectRow[];
}

export const recruitingApi = {
  pipeline: (sid: string, grade = "12th") =>
    apiGet<PipelineResponse>(
      `/sessions/${sid}/dynasty/recruiting-pipeline?grade=${encodeURIComponent(grade)}`,
    ),
};

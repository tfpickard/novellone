import type { PageLoad } from './$types';
import { getStoryRecommendations } from '$lib/api';

export type MetricStory = {
  story_id: string;
  title: string;
  status: string;
  cover_image_url: string | null;
  chapter_count: number;
  completed_at: string | null;
  last_activity_at: string | null;
  total_tokens: number | null;
  latest_chapter_number: number | null;
  premise: string | null;
  genre_tags: string[] | null;
  style_authors: string[] | null;
  narrative_perspective: string | null;
  tone: string | null;
  estimated_reading_time_minutes: number | null;
  value: number | null;
  trend_change: number | null;
  trend_samples: number[] | null;
};

export type MetricExtremes = {
  key: string;
  label: string;
  description?: string | null;
  group: string;
  order: number;
  unit?: string | null;
  decimals: number;
  higher_is_better: boolean;
  priority: boolean;
  best: MetricStory | null;
  worst: MetricStory | null;
};

export type RecommendationsResponse = {
  metrics: MetricExtremes[];
};

export const load: PageLoad = async () => {
  const recommendations = (await getStoryRecommendations()) as RecommendationsResponse;
  return { recommendations };
};

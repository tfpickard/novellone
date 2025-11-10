import type { PageLoad } from './$types';
import { getStoryRecommendations } from '$lib/api';

export type MetricStory = {
  story_id: string;
  title: string;
  status: string;
  cover_image_url: string | null;
  chapter_count: number;
  completed_at: string | null;
  value: number | null;
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

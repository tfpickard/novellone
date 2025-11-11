export const CONTENT_AXIS_KEYS = [
  'sexual_content',
  'violence',
  'strong_language',
  'drug_use',
  'horror_suspense',
  'gore_graphic_imagery',
  'romance_focus',
  'crime_illicit_activity',
  'political_ideology',
  'supernatural_occult'
] as const;

export type ContentAxisKey = (typeof CONTENT_AXIS_KEYS)[number];

export type ContentAxisSettings = {
  average_level: number;
  momentum: number;
  premise_multiplier: number;
};

export type ContentAxisSettingsMap = Record<ContentAxisKey, ContentAxisSettings>;

export type ContentAxisLevelMap = Partial<Record<ContentAxisKey, number>>;

export const CONTENT_AXIS_METADATA: Record<ContentAxisKey, { label: string; description: string; color: string }> = {
  sexual_content: {
    label: 'Sexual Content',
    description: 'Depictions of intimacy, sensuality, and erotic tension.',
    color: '#f97316'
  },
  violence: {
    label: 'Violence & Combat',
    description: 'Physical conflict, battle scenes, and perilous encounters.',
    color: '#ef4444'
  },
  strong_language: {
    label: 'Strong Language',
    description: 'Profanity, coarse language, and verbal intensity.',
    color: '#6366f1'
  },
  drug_use: {
    label: 'Drug & Substance Use',
    description: 'Mood-altering substances, addiction, and related themes.',
    color: '#10b981'
  },
  horror_suspense: {
    label: 'Horror & Suspense',
    description: 'Unease, dread, supernatural tension, and psychological thrills.',
    color: '#8b5cf6'
  },
  gore_graphic_imagery: {
    label: 'Gore & Graphic Imagery',
    description: 'Explicit bodily harm, viscera, and visceral description.',
    color: '#be123c'
  },
  romance_focus: {
    label: 'Romance Focus',
    description: 'Relationships, longing, and emotional intimacy in focus.',
    color: '#ec4899'
  },
  crime_illicit_activity: {
    label: 'Crime & Illicit Activity',
    description: 'Heists, conspiracies, underground dealings, and lawlessness.',
    color: '#0ea5e9'
  },
  political_ideology: {
    label: 'Political & Ideological Themes',
    description: 'Power struggles, governance, activism, and philosophy.',
    color: '#facc15'
  },
  supernatural_occult: {
    label: 'Supernatural & Occult',
    description: 'Mythic forces, arcane rituals, and beyond-the-veil encounters.',
    color: '#14b8a6'
  }
};

export const CONTENT_AXIS_DEFAULTS: ContentAxisSettingsMap = CONTENT_AXIS_KEYS.reduce(
  (acc, axis) => {
    acc[axis] = { average_level: 2, momentum: 0, premise_multiplier: 1 };
    return acc;
  },
  {} as ContentAxisSettingsMap
);

const AXIS_KEY_SET = new Set<string>(CONTENT_AXIS_KEYS);

function clamp(value: number, min: number, max: number): number {
  return Math.max(min, Math.min(max, value));
}

function toNumber(value: unknown, fallback: number): number {
  if (typeof value === 'number' && Number.isFinite(value)) return value;
  if (typeof value === 'string') {
    const parsed = Number(value.trim());
    if (!Number.isNaN(parsed)) return parsed;
  }
  return fallback;
}

export function sanitizeContentAxisSettings(
  raw: Partial<Record<string, Partial<ContentAxisSettings>>> | null | undefined
): ContentAxisSettingsMap {
  const result: ContentAxisSettingsMap = { ...CONTENT_AXIS_DEFAULTS };
  if (!raw) {
    return result;
  }
  for (const [axis, payload] of Object.entries(raw)) {
    if (!AXIS_KEY_SET.has(axis) || !payload) continue;
    const key = axis as ContentAxisKey;
    const defaults = CONTENT_AXIS_DEFAULTS[key];
    const average = clamp(toNumber(payload.average_level, defaults.average_level), 0, 10);
    const momentum = clamp(toNumber(payload.momentum, defaults.momentum), -1, 1);
    const multiplier = clamp(toNumber(payload.premise_multiplier, defaults.premise_multiplier), 0, 10);
    result[key] = {
      average_level: Number(average.toFixed(3)),
      momentum: Number(momentum.toFixed(3)),
      premise_multiplier: Number(multiplier.toFixed(3))
    };
  }
  return result;
}

export function sanitizeContentLevels(
  raw: Record<string, unknown> | null | undefined
): ContentAxisLevelMap {
  const entries: ContentAxisLevelMap = {};
  if (!raw) {
    return entries;
  }
  for (const [axis, value] of Object.entries(raw)) {
    if (!AXIS_KEY_SET.has(axis)) continue;
    const numeric = toNumber(value, Number.NaN);
    if (Number.isNaN(numeric)) continue;
    entries[axis as ContentAxisKey] = clamp(Number(numeric.toFixed(3)), 0, 10);
  }
  return entries;
}

export function getTopContentAxes(
  raw: Record<string, unknown> | null | undefined,
  limit = 3
): Array<{ key: ContentAxisKey; value: number }> {
  const levels = sanitizeContentLevels(raw);
  const pairs = Object.entries(levels) as Array<[ContentAxisKey, number]>;
  return pairs
    .sort((a, b) => b[1] - a[1])
    .filter(([, value]) => value > 0)
    .slice(0, limit)
    .map(([key, value]) => ({ key, value }));
}

export function formatContentLevel(value: number | null | undefined, digits = 1): string {
  if (value === null || value === undefined || Number.isNaN(value)) {
    return '—';
  }
  return value.toFixed(digits);
}

export function sortAxesByLabel(keys: ContentAxisKey[] = CONTENT_AXIS_KEYS): ContentAxisKey[] {
  return [...keys].sort((a, b) => {
    const labelA = CONTENT_AXIS_METADATA[a].label;
    const labelB = CONTENT_AXIS_METADATA[b].label;
    return labelA.localeCompare(labelB);
  });
}

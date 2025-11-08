export type StoryTheme = {
  primary_color: string;
  secondary_color: string;
  background_color: string;
  text_color: string;
  text_secondary: string;
  accent_color: string;
  border_color: string;
  card_background: string;
  font_heading: string;
  font_body: string;
  aesthetic: string;
  mood: string;
  border_radius: string;
  shadow_style: string;
  animation_speed: string;
  [key: string]: string;
};

export function applyStoryTheme(theme: StoryTheme, element: HTMLElement): void {
  if (!theme || !element) return;
  const root = element.style;
  Object.entries(theme).forEach(([key, value]) => {
    const cssVar = `--${key.replace(/_/g, '-')}`;
    root.setProperty(cssVar, value);
  });
}

export function createThemeAction(theme?: StoryTheme) {
  return function apply(node: HTMLElement) {
    if (theme) {
      applyStoryTheme(theme, node);
    }
    return {
      update(newTheme?: StoryTheme) {
        if (newTheme) {
          applyStoryTheme(newTheme, node);
        }
      }
    };
  };
}

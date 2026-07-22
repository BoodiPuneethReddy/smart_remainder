/**
 * design-tokens.ts — Single source of truth for all design values.
 *
 * RULE: Every component imports from here. No hardcoded hex, px, or shadow
 * values anywhere in component files. If a value isn't here, add it here first.
 *
 * These TypeScript values mirror the CSS variables in src/index.css exactly.
 * Use CSS variables in className strings; use these TS values in inline styles
 * or JavaScript logic (e.g., chart configs, canvas draws).
 */

// ── Colors ──────────────────────────────────────────────────────────────────
export const colors = {
  // Backgrounds
  bgPrimary:   '#0B0E14',
  bgSecondary: '#12141C',

  // Card surfaces (glassmorphism)
  cardBg:     'rgba(255,255,255,0.05)',
  cardBorder: 'rgba(255,255,255,0.08)',
  cardHover:  'rgba(255,255,255,0.08)',
  cardActive: 'rgba(255,255,255,0.12)',

  // Priority tiers — the visual hero of the app
  priorityHigh:   '#FF6B35',
  priorityMedium: '#FFC857',
  priorityLow:    '#2EC4B6',

  // Text
  textPrimary:   '#F5F7FA',
  textSecondary: '#98A2B3',
  textMuted:     '#64748B',

  // Semantic
  success:  '#2EC4B6',
  warning:  '#FFC857',
  danger:   '#FF6B35',
  info:     '#5B8DEF',

  // Interactive states
  focusRing:     'rgba(91,141,239,0.5)',
  surfaceHover:  'rgba(255,255,255,0.08)',
  surfaceActive: 'rgba(255,255,255,0.12)',
} as const;

// ── Typography ───────────────────────────────────────────────────────────────
export const typography = {
  fontFamily: 'Inter, system-ui, -apple-system, sans-serif',
  sizes: {
    display: '36px',
    h1:      '28px',
    h2:      '20px',
    h3:      '16px',
    body:    '14px',
    bodySm:  '13px',
    caption: '12px',
  },
  weights: {
    normal:   400,
    medium:   500,
    semibold: 600,
    bold:     700,
  },
  lineHeights: {
    tight:  1.2,
    normal: 1.5,
  },
} as const;

// ── Spacing (4px base scale) ──────────────────────────────────────────────────
export const spacing = {
  1:  '4px',
  2:  '8px',
  3:  '12px',
  4:  '16px',
  6:  '24px',
  8:  '32px',
  12: '48px',
  16: '64px',
  // Semantic aliases
  cardPadding:    '24px',
  sectionGap:     '32px',
  pageMargin:     '48px',
  pageMarginMobile: '16px',
} as const;

// ── Border Radius ─────────────────────────────────────────────────────────────
export const radius = {
  card:  '24px',
  input: '14px',
  badge: '8px',
  full:  '9999px',
} as const;

// ── Elevation / Shadows ───────────────────────────────────────────────────────
export const shadows = {
  flat:        'none',
  raised:      '0 4px 16px rgba(0,0,0,0.24)',
  raisedHover: '0 8px 24px rgba(0,0,0,0.32)',
  floating:    '0 12px 32px rgba(0,0,0,0.40)',
  highGlow:    '0 0 24px rgba(255,107,53,0.18)',
  mediumGlow:  '0 0 24px rgba(255,200,87,0.14)',
  lowGlow:     '0 0 24px rgba(46,196,182,0.14)',
} as const;

// ── Priority score → color + tier mapping (used by TaskCard + charts) ────────
export type PriorityTier = 'critical' | 'high' | 'medium' | 'low';

export function getPriorityTier(score: number): PriorityTier {
  if (score >= 75) return 'critical';
  if (score >= 55) return 'high';
  if (score >= 35) return 'medium';
  return 'low';
}

export function getPriorityColor(score: number): string {
  const tier = getPriorityTier(score);
  if (tier === 'critical' || tier === 'high') return colors.priorityHigh;
  if (tier === 'medium') return colors.priorityMedium;
  return colors.priorityLow;
}

export function getPriorityLabel(score: number): string {
  const tier = getPriorityTier(score);
  if (tier === 'critical') return 'Critical';
  if (tier === 'high') return 'High';
  if (tier === 'medium') return 'Medium';
  return 'Low';
}

// ── Chart theme — imported by every Recharts instance ────────────────────────
export const chartTheme = {
  backgroundColor: 'transparent',
  gridColor:       'rgba(255,255,255,0.06)',
  axisColor:       colors.textSecondary,
  tooltipBg:       '#1A1E2A',
  tooltipBorder:   colors.cardBorder,
  tooltipText:     colors.textPrimary,
  colors: [colors.priorityHigh, colors.priorityMedium, colors.priorityLow, colors.info],
  priorityColors: {
    critical: colors.priorityHigh,
    high:     colors.priorityHigh,
    medium:   colors.priorityMedium,
    low:      colors.priorityLow,
  },
} as const;

// ── Task type → display label ─────────────────────────────────────────────────
export const taskTypeLabels: Record<string, string> = {
  exam:       'Exam',
  project:    'Project',
  assignment: 'Assignment',
  quiz:       'Quiz',
  homework:   'Homework',
  reading:    'Reading',
};

export const taskTypeColors: Record<string, string> = {
  exam:       colors.priorityHigh,
  project:    colors.priorityMedium,
  assignment: colors.info,
  quiz:       colors.priorityMedium,
  homework:   colors.priorityLow,
  reading:    colors.textSecondary,
};

/**
 * DevSweep AI Design Tokens
 * Single source of truth for spacing, typography, colors, and semantic values.
 * Used by both Simple and Technical views.
 */

// ============================================================================
// SPACING SCALE (4px base)
// ============================================================================
export const spacing = {
  xs: '4px',    // 1
  sm: '8px',    // 2
  md: '16px',   // 4
  lg: '24px',   // 6
  xl: '32px',   // 8
  xxl: '48px',  // 12
  xxxl: '64px', // 16
} as const;

export type SpacingKey = keyof typeof spacing;

// ============================================================================
// TYPOGRAPHY SCALE
// ============================================================================
export const typography = {
  // Display / Headlines
  display: 'text-4xl font-bold tracking-tight',
  h1: 'text-3xl font-bold',
  h2: 'text-2xl font-semibold',
  h3: 'text-xl font-semibold',
  h4: 'text-lg font-medium',

  // Body
  body: 'text-base leading-relaxed',
  bodySm: 'text-sm leading-normal',
  caption: 'text-xs leading-normal',

  // Monospace (code, paths, sizes)
  mono: 'font-mono text-sm',
  monoXs: 'font-mono text-xs',
  monoBase: 'font-mono text-base',

  // Interactive
  button: 'font-medium text-sm',
  link: 'text-sm underline-offset-2 hover:underline',
} as const;

export type TypographyKey = keyof typeof typography;

// ============================================================================
// SEMANTIC COLORS (Light + Dark)
// ============================================================================
export const colors = {
  light: {
    // Backgrounds
    bg: '#ffffff',
    bgSecondary: '#f6f8fa',
    bgTertiary: '#eaeef2',
    bgHover: '#f3f4f6',

    // Borders
    border: '#d0d7de',
    borderHover: '#8b949e',
    borderFocus: '#0969da',

    // Text
    text: '#1f2328',
    textSecondary: '#656d76',
    textMuted: '#59636e',
    textInverse: '#ffffff',

    // Brand
    accent: '#0969da',
    accentHover: '#0860ca',
    accentLight: '#dbeafe',

    // Status
    success: '#1a7f37',
    successLight: '#dcfce7',
    warning: '#9a6700',
    warningLight: '#fef3c7',
    danger: '#cf222e',
    dangerHover: '#a40e26',
    dangerLight: '#fee2e2',
    info: '#0550ae',
    infoLight: '#dbeafe',

    // Overlay
    overlay: 'rgba(15, 23, 42, 0.5)',
  },
  dark: {
    // Backgrounds
    bg: '#0d1117',
    bgSecondary: '#161b22',
    bgTertiary: '#21262d',
    bgHover: '#30363d',

    // Borders
    border: '#30363d',
    borderHover: '#484f58',
    borderFocus: '#58a6ff',

    // Text
    text: '#f0f6fc',
    textSecondary: '#8b949e',
    textMuted: '#8b949e',
    textInverse: '#0d1117',

    // Brand
    accent: '#58a6ff',
    accentHover: '#79b8ff',
    accentLight: '#1f3a5f',

    // Status
    success: '#3fb950',
    successLight: '#0f2e1a',
    warning: '#d29922',
    warningLight: '#3d2e0a',
    danger: '#f85149',
    dangerHover: '#ff7b72',
    dangerLight: '#3d1a1a',
    info: '#58a6ff',
    infoLight: '#1f3a5f',

    // Overlay
    overlay: 'rgba(0, 0, 0, 0.7)',
  },
} as const;

export type ColorMode = 'light' | 'dark';
export type ColorKey = keyof typeof colors.light;

// ============================================================================
// RISK SEMANTICS (Consistent across views)
// ============================================================================
export const riskSemantics = {
  SAFE: {
    label: 'Safe',
    shortLabel: 'Safe',
    description: 'Regenerable with standard commands. No source code or configuration affected.',
    icon: '✓',
    color: 'success',
    bg: 'successLight',
    border: 'success',
    // Consequences
    consequences: 'Next build/install will re-download or regenerate. May take several minutes.',
    regenerable: true,
  },
  CAUTION: {
    label: 'Caution',
    shortLabel: 'Caution',
    description: 'Likely regenerable but verify before removing. May contain project-specific data.',
    icon: '⚠',
    color: 'warning',
    bg: 'warningLight',
    border: 'warning',
    consequences: 'May require manual reconfiguration. Verify project still works after removal.',
    regenerable: true,
  },
  DANGEROUS: {
    label: 'Dangerous',
    shortLabel: 'Dangerous',
    description: 'Contains source code, credentials, or irreplaceable data. Never delete.',
    icon: '✕',
    color: 'danger',
    bg: 'dangerLight',
    border: 'danger',
    consequences: 'Data loss. Project may not build or run. Cannot be automatically recovered.',
    regenerable: false,
  },
} as const;

export type RiskLevel = keyof typeof riskSemantics;

// ============================================================================
// COMPONENT VARIANTS
// ============================================================================
export const buttonVariants = {
  primary: 'bg-devsweep-accent text-devsweep-bg hover:bg-devsweep-accentHover',
  secondary: 'bg-devsweep-bgTertiary text-devsweep-text border border-devsweep-border hover:bg-devsweep-bgHover',
  ghost: 'text-devsweep-textSecondary hover:text-devsweep-text hover:bg-devsweep-bgTertiary',
  danger: 'bg-devsweep-danger/10 text-devsweep-danger border border-devsweep-danger/20 hover:bg-devsweep-danger/20',
  success: 'bg-devsweep-success/10 text-devsweep-success border border-devsweep-success/20 hover:bg-devsweep-success/20',
  outline: 'bg-transparent text-devsweep-text border border-devsweep-border hover:bg-devsweep-bgTertiary',
} as const;

export const buttonSizes = {
  sm: 'px-3 py-1.5 text-sm',
  md: 'px-4 py-2 text-sm',
  lg: 'px-6 py-3 text-base',
  xl: 'px-8 py-4 text-lg',
} as const;

export const cardVariants = {
  default: 'bg-devsweep-bgSecondary border border-devsweep-border',
  outlined: 'bg-devsweep-bg border border-devsweep-border',
  elevated: 'bg-devsweep-bgSecondary border border-devsweep-border shadow-lg',
  subtle: 'bg-devsweep-bgTertiary/50 border border-devsweep-border/50',
} as const;

export const badgeVariants = {
  risk: {
    SAFE: 'bg-devsweep-success/10 text-devsweep-success border border-devsweep-success/20',
    CAUTION: 'bg-devsweep-warning/10 text-devsweep-warning border border-devsweep-warning/20',
    DANGEROUS: 'bg-devsweep-danger/10 text-devsweep-danger border border-devsweep-danger/20',
  },
  status: {
    active: 'bg-devsweep-success/10 text-devsweep-success',
    inactive: 'bg-devsweep-textMuted/10 text-devsweep-textMuted',
    pending: 'bg-devsweep-warning/10 text-devsweep-warning',
    error: 'bg-devsweep-danger/10 text-devsweep-danger',
  },
  info: 'bg-devsweep-accent/10 text-devsweep-accent border border-devsweep-accent/20',
} as const;

// ============================================================================
// BREAKPOINTS
// ============================================================================
export const breakpoints = {
  sm: '640px',
  md: '768px',
  lg: '1024px',
  xl: '1280px',
  '2xl': '1536px',
} as const;

// ============================================================================
// ANIMATION / TRANSITION
// ============================================================================
export const transitions = {
  fast: '150ms ease-out',
  normal: '200ms ease-out',
  slow: '300ms ease-out',
} as const;

export const animations = {
  fadeIn: 'animate-in fade-in-0 duration-200',
  slideUp: 'animate-in slide-in-from-bottom-2 duration-200',
  slideDown: 'animate-in slide-in-from-top-2 duration-200',
  scaleIn: 'animate-in zoom-in-95 duration-200',
} as const;

// ============================================================================
// Z-INDEX SCALE
// ============================================================================
export const zIndex = {
  base: 0,
  dropdown: 10,
  sticky: 20,
  modal: 30,
  popover: 40,
  tooltip: 50,
  toast: 60,
} as const;

// ============================================================================
// ICON SIZES
// ============================================================================
export const iconSizes = {
  xs: 'w-3 h-3',
  sm: 'w-4 h-4',
  md: 'w-5 h-5',
  lg: 'w-6 h-6',
  xl: 'w-8 h-8',
  xxl: 'w-12 h-12',
} as const;

// ============================================================================
// BORDER RADIUS
// ============================================================================
export const borderRadius = {
  sm: 'rounded',
  md: 'rounded-lg',
  lg: 'rounded-xl',
  xl: 'rounded-2xl',
  full: 'rounded-full',
} as const;

// ============================================================================
// SHADOWS
// ============================================================================
export const shadows = {
  sm: 'shadow-sm',
  md: 'shadow',
  lg: 'shadow-lg',
  xl: 'shadow-xl',
  inner: 'shadow-inner',
} as const;

// ============================================================================
// FOCUS RING
// ============================================================================
export const focusRing = 'focus:outline-none focus:ring-2 focus:ring-devsweep-accent focus:ring-offset-2 focus:ring-offset-devsweep-bg';

// Dark mode focus ring
export const focusRingDark = 'focus:outline-none focus:ring-2 focus:ring-devsweep-accent focus:ring-offset-2 focus:ring-offset-devsweep-bg';

// ============================================================================
// UTILITY: Get risk semantics with fallbacks
// ============================================================================
export function getRiskSemantics(risk: string): (typeof riskSemantics)['SAFE' | 'CAUTION' | 'DANGEROUS'] {
  const key = risk.toUpperCase() as RiskLevel;
  return riskSemantics[key] || riskSemantics.CAUTION;
}

// ============================================================================
// UTILITY: Format bytes (single source of truth)
// ============================================================================
export function formatBytes(bytes: number): string {
  if (bytes === 0) return '0 B';
  const k = 1024;
  const sizes = ['B', 'KB', 'MB', 'GB', 'TB'];
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  return `${parseFloat((bytes / Math.pow(k, i)).toFixed(1))} ${sizes[i]}`;
}

// ============================================================================
// UTILITY: Format duration
// ============================================================================
export function formatDuration(seconds: number): string {
  if (seconds < 60) return `${seconds}s`;
  if (seconds < 3600) return `${Math.floor(seconds / 60)}m ${seconds % 60}s`;
  return `${Math.floor(seconds / 3600)}h ${Math.floor((seconds % 3600) / 60)}m`;
}

// ============================================================================
// UTILITY: Get Tailwind color class for semantic color
// ============================================================================
export function getColorClass(colorKey: ColorKey, mode: ColorMode = 'dark'): string {
  const color = colors[mode][colorKey];
  // This is a mapping helper - actual Tailwind classes use the CSS variables
  return `devsweep-${colorKey}`;
}

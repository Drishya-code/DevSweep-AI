/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  darkMode: 'class',
  theme: {
    extend: {
      colors: {
        devsweep: Object.fromEntries([
          'bg', 'bgSecondary', 'bgTertiary', 'bgHover', 'border', 'borderHover', 'borderFocus',
          'text', 'textSecondary', 'textMuted', 'textInverse', 'accent', 'accentHover', 'accentLight',
          'success', 'successLight', 'warning', 'warningLight', 'danger', 'dangerHover', 'dangerLight',
          'info', 'infoLight', 'overlay',
        ].map(token => [token, `rgb(var(--devsweep-${token}) / <alpha-value>)`])),
      },
      fontFamily: {
        mono: ['JetBrains Mono', 'Fira Code', 'Consolas', 'monospace'],
        sans: ['Inter', 'system-ui', '-apple-system', 'sans-serif'],
      },
      animation: {
        'pulse-slow': 'pulse 3s cubic-bezier(0.4, 0, 0.6, 1) infinite',
        'spin-slow': 'spin 2s linear infinite',
        'fade-in': 'fade-in 0.2s ease-out forwards',
        'slide-up': 'slide-up 0.2s ease-out forwards',
        'slide-down': 'slide-down 0.2s ease-out forwards',
        'scale-in': 'scale-in 0.2s ease-out forwards',
      },
      keyframes: {
        'fade-in': {
          '0%': { opacity: '0' },
          '100%': { opacity: '1' },
        },
        'slide-up': {
          '0%': { opacity: '0', transform: 'translateY(8px)' },
          '100%': { opacity: '1', transform: 'translateY(0)' },
        },
        'slide-down': {
          '0%': { opacity: '0', transform: 'translateY(-8px)' },
          '100%': { opacity: '1', transform: 'translateY(0)' },
        },
        'scale-in': {
          '0%': { opacity: '0', transform: 'scale(0.95)' },
          '100%': { opacity: '1', transform: 'scale(1)' },
        },
      },
      transitionDuration: {
        'fast': '150ms',
        'normal': '200ms',
        'slow': '300ms',
      },
      zIndex: {
        'base': '0',
        'dropdown': '10',
        'sticky': '20',
        'modal': '30',
        'popover': '40',
        'tooltip': '50',
        'toast': '60',
      },
    },
  },
  plugins: [],
}

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
        devsweep: {
          bg: '#0d1117',
          bgSecondary: '#161b22',
          bgTertiary: '#21262d',
          border: '#30363d',
          borderHover: '#484f58',
          text: '#f0f6fc',
          textSecondary: '#8b949e',
          textMuted: '#6e7681',
          accent: '#58a6ff',
          accentHover: '#79b8ff',
          success: '#3fb950',
          warning: '#d29922',
          danger: '#f85149',
          dangerHover: '#ff7b72',
        },
      },
      fontFamily: {
        mono: ['JetBrains Mono', 'Fira Code', 'Consolas', 'monospace'],
        sans: ['Inter', 'system-ui', '-apple-system', 'sans-serif'],
      },
      animation: {
        'pulse-slow': 'pulse 3s cubic-bezier(0.4, 0, 0.6, 1) infinite',
        'spin-slow': 'spin 2s linear infinite',
      },
    },
  },
  plugins: [],
}
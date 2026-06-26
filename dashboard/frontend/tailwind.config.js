/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        void: '#0a0a0c',
        panel: '#141418',
        grid: '#252529',
        tactical: {
          text: '#e4e4e7',
          muted: '#52525b',
          dim: '#3f3f46',
        },
        accent: {
          yellow: '#F4D35E',
          yorange: '#F2A541',
          orange: '#EE6C2C',
          redorange: '#E8402B',
          red: '#C62828'
        }
      },
      fontFamily: {
        mono: ['"JetBrains Mono"', 'monospace'],
        sans: ['Inter', '-apple-system', 'BlinkMacSystemFont', 'Segoe UI', 'Roboto', 'sans-serif'],
      },
      borderRadius: {
        none: '0px',
      }
    },
  },
  plugins: [],
}

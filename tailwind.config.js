/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        cream: {
          DEFAULT: '#F5F3EC',
          dark: '#E8E4D8',
          light: '#FAF8F3',
        },
        surface: {
          DEFAULT: '#FFFFFF',
          light: '#FAF8F4',
        },
        beige: {
          DEFAULT: '#EADFCB',
          muted: '#DFCFB5',
          deep: '#D4C0A2',
        },
        charcoal: {
          DEFAULT: '#141619',
          light: '#1F2328',
          muted: '#4B535E',
          subtle: '#6E7785',
        },
        border: {
          warm: '#D9D0BE',
          subtle: 'rgba(20, 22, 25, 0.12)',
          strong: 'rgba(20, 22, 25, 0.24)',
        },
        accent: {
          olive: '#385C2E',
          'olive-dark': '#26421E',
          forest: '#1C3A24',
          terracotta: '#AC3B1E',
          amber: '#C47D17',
          blue: '#1E588E',
          indigo: '#3B3691',
          sand: '#CBB28D',
        },
        tint: {
          olive: '#EAF3E6',
          'olive-border': '#ADD3A4',
          'olive-text': '#1F4517',
          
          amber: '#FAF0D6',
          'amber-border': '#F2D08E',
          'amber-text': '#7A4B06',

          terracotta: '#FCEBE6',
          'terracotta-border': '#F5B8A8',
          'terracotta-text': '#8C270F',

          slate: '#E8F1FC',
          'slate-border': '#A6CCF2',
          'slate-text': '#103B66',

          indigo: '#EEECFA',
          'indigo-border': '#BDB7F5',
          'indigo-text': '#2A237A',

          emerald: '#E4F7ED',
          'emerald-border': '#9DE0BC',
          'emerald-text': '#0F4E2E',
        },
        status: {
          operational: '#385C2E',
          attention: '#C47D17',
          critical: '#AC3B1E',
          offline: '#6E7785',
        }
      },
      fontFamily: {
        serif: ['"Fraunces"', '"Outfit"', 'Georgia', 'serif'],
        display: ['"Fraunces"', '"Outfit"', 'serif'],
        sans: ['"Outfit"', '"Sora"', '"Manrope"', 'sans-serif'],
        body: ['"Manrope"', '"Outfit"', 'sans-serif'],
        mono: ['"IBM Plex Mono"', 'monospace'],
      },
      boxShadow: {
        subtle: '0 2px 4px rgba(20, 22, 25, 0.05), 0 1px 2px rgba(20, 22, 25, 0.03)',
        card: '0 4px 10px rgba(20, 22, 25, 0.06), 0 1px 3px rgba(20, 22, 25, 0.03)',
        dropdown: '0 8px 24px rgba(20, 22, 25, 0.12)',
      },
      borderRadius: {
        DEFAULT: '10px',
        'sm': '6px',
        'md': '10px',
        'lg': '14px',
        'xl': '18px',
        '2xl': '24px',
      }
    },
  },
  plugins: [],
}

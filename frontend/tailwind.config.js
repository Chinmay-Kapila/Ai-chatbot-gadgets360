/** @type {import('tailwindcss').Config} */
export default {
  darkMode: 'class',
  content: ['./index.html', './src/**/*.{js,jsx}'],
  theme: {
    extend: {
      colors: {
        brand: {
          50: '#FDECEA',
          100: '#FBD2CD',
          200: '#F5A89D',
          300: '#EF7C6A',
          400: '#E85A42',
          500: '#E03A22', // primary signal red
          600: '#C22A17',
          700: '#9C2113',
          800: '#761911',
          900: '#4F110B',
        },
        ink: {
          DEFAULT: '#14161A',
          50: '#F7F7F8',
          100: '#ECEDEF',
          200: '#D6D8DC',
          300: '#B3B7BE',
          400: '#82868F',
          500: '#5B5F68',
          600: '#41444C',
          700: '#2C2F35',
          800: '#1D2026',
          900: '#14161A',
          950: '#0B0C0F',
        },
        signal: {
          amber: '#F5A623',
          green: '#22C55E',
        },
      },
      fontFamily: {
        display: ['"Sora"', 'system-ui', 'sans-serif'],
        body: ['"Inter"', 'system-ui', 'sans-serif'],
        mono: ['"JetBrains Mono"', 'ui-monospace', 'monospace'],
      },
      boxShadow: {
        panel: '0 20px 60px -15px rgba(20, 22, 26, 0.35)',
        launcher: '0 10px 30px -6px rgba(224, 58, 34, 0.55)',
      },
      keyframes: {
        pulseRing: {
          '0%': { transform: 'scale(0.85)', opacity: '0.7' },
          '70%': { transform: 'scale(1.6)', opacity: '0' },
          '100%': { transform: 'scale(1.6)', opacity: '0' },
        },
        typingDot: {
          '0%, 60%, 100%': { transform: 'translateY(0)', opacity: '0.4' },
          '30%': { transform: 'translateY(-4px)', opacity: '1' },
        },
        slideUp: {
          '0%': { transform: 'translateY(16px)', opacity: '0' },
          '100%': { transform: 'translateY(0)', opacity: '1' },
        },
        fadeIn: {
          '0%': { opacity: '0' },
          '100%': { opacity: '1' },
        },
      },
      animation: {
        pulseRing: 'pulseRing 2.4s cubic-bezier(0.4, 0, 0.6, 1) infinite',
        typingDot: 'typingDot 1.2s ease-in-out infinite',
        slideUp: 'slideUp 0.28s cubic-bezier(0.16, 1, 0.3, 1)',
        fadeIn: 'fadeIn 0.2s ease-out',
      },
      borderRadius: {
        xl2: '1.25rem',
      },
    },
  },
  plugins: [],
}

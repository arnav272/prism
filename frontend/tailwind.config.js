/** @type {import('tailwindcss').Config} */
module.exports = {
  content: ['./src/**/*.{js,ts,jsx,tsx,mdx}'],
  theme: {
    extend: {
      fontFamily: {
        display: ['General Sans', 'sans-serif'],
        body:    ['Instrument Sans', 'sans-serif'],
        mono:    ['DM Mono', 'monospace'],
      },
      colors: {
        ink:          '#07060f',
        surface:      '#0d0c18',
        panel:        '#13121f',
        border:       '#1c1b2e',
        muted:        '#252438',
        accent:       '#e8ff47',
        'accent-dim': '#b8cc38',
        signal:       '#ff6b35',
        sky:          '#818cf8',
        ghost:        '#6b6a8a',
        text:         '#eeedf5',
        'hero-sub':   '#b0afc8',
      },
      animation: {
        'fade-up':   'fadeUp 0.5s ease forwards',
        'pulse-dot': 'pulseDot 1.4s ease-in-out infinite',
        'marquee':   'marquee 22s linear infinite',
      },
      keyframes: {
        fadeUp: {
          '0%':   { opacity: '0', transform: 'translateY(16px)' },
          '100%': { opacity: '1', transform: 'translateY(0)' },
        },
        pulseDot: {
          '0%, 80%, 100%': { transform: 'scale(0.6)', opacity: '0.3' },
          '40%':           { transform: 'scale(1)',   opacity: '1' },
        },
        marquee: {
          'from': { transform: 'translateX(0%)' },
          'to':   { transform: 'translateX(-50%)' },
        },
      },
    },
  },
  plugins: [],
}

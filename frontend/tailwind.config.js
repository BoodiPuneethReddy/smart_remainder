/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{ts,tsx}'],
  theme: {
    extend: {
      // ── Design token extensions ─────────────────────────────────────────────
      // All values mirror the CSS variables in src/index.css.
      // Components reference CSS variables directly; these extensions expose
      // the same tokens in Tailwind utility classes.
      colors: {
        bg: {
          primary: '#0B0E14',
          secondary: '#12141C',
        },
        card: {
          DEFAULT: 'rgba(255,255,255,0.05)',
          border: 'rgba(255,255,255,0.08)',
          hover: 'rgba(255,255,255,0.08)',
          active: 'rgba(255,255,255,0.12)',
        },
        priority: {
          high: '#FF6B35',
          medium: '#FFC857',
          low: '#2EC4B6',
        },
        text: {
          primary: '#F5F7FA',
          secondary: '#98A2B3',
        },
        success: '#2EC4B6',
        warning: '#FFC857',
        danger: '#FF6B35',
        info: '#5B8DEF',
      },
      fontFamily: {
        sans: ['Inter', 'system-ui', '-apple-system', 'sans-serif'],
      },
      fontSize: {
        display: ['36px', { lineHeight: '1.2', fontWeight: '700' }],
        h1:      ['28px', { lineHeight: '1.2', fontWeight: '600' }],
        h2:      ['20px', { lineHeight: '1.2', fontWeight: '600' }],
        h3:      ['16px', { lineHeight: '1.4', fontWeight: '600' }],
        body:    ['14px', { lineHeight: '1.5', fontWeight: '400' }],
        'body-sm': ['13px', { lineHeight: '1.5', fontWeight: '400' }],
        caption: ['12px', { lineHeight: '1.4', fontWeight: '500' }],
      },
      spacing: {
        // 4px-based scale — the only spacing values used in the app
        1: '4px',
        2: '8px',
        3: '12px',
        4: '16px',
        6: '24px',
        8: '32px',
        12: '48px',
        16: '64px',
      },
      borderRadius: {
        card:  '24px',
        input: '14px',
        badge: '8px',
        full:  '9999px',
      },
      boxShadow: {
        flat:     'none',
        raised:   '0 4px 16px rgba(0,0,0,0.24)',
        floating: '0 12px 32px rgba(0,0,0,0.40)',
        // Hover lift — raised → slightly stronger
        'raised-hover': '0 8px 24px rgba(0,0,0,0.32)',
        // Priority-colored glows
        'high-glow':   '0 0 24px rgba(255,107,53,0.18)',
        'medium-glow': '0 0 24px rgba(255,200,87,0.14)',
        'low-glow':    '0 0 24px rgba(46,196,182,0.14)',
      },
      backdropBlur: {
        card: '12px',
      },
      animation: {
        shimmer: 'shimmer 1.8s linear infinite',
        'fade-in': 'fadeIn 0.2s ease-out',
        'spin-slow': 'spin 2s linear infinite',
      },
      keyframes: {
        shimmer: {
          '0%':   { backgroundPosition: '-400px 0' },
          '100%': { backgroundPosition: '400px 0' },
        },
        fadeIn: {
          '0%':   { opacity: '0', transform: 'translateY(6px)' },
          '100%': { opacity: '1', transform: 'translateY(0)' },
        },
      },
    },
  },
  plugins: [],
}

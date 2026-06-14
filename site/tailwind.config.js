/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{ts,tsx}'],
  theme: {
    extend: {
      fontFamily: {
        serif: ['"DM Serif Display"', 'serif'],
      },
      colors: {
        // Core surfaces — clean white
        cream:     '#FFFFFF',   // body shell
        parchment: '#FAFAFA',   // detail pane (subtle off-white to differentiate)
        'match-bg':'#F4F4F4',   // match card
        sand:      '#E2E2E2',   // borders

        // Header — teal (unchanged)
        header:        '#A8D8D0',
        'header-border':'#8ECAC0',

        // Row states
        'row-selected':'#EDEDED',
        'row-hover':   '#F5F5F5',

        // Tier indicators (unchanged)
        'tier-green':  '#8ABF78',
        'tier-amber':  '#C4A96A',
        'tier-gray':   '#ABABAB',

        // Skill / JD highlight (unchanged — semantic colors)
        'skill-bg':    '#EDF5E8',
        'skill-text':  '#5A8A4A',
        'skill-border':'#DEDEDE',
        'jd-key':      '#2E6E78',

        // New / Sponsor badges (unchanged — semantic)
        'badge-new-bg':      '#EDF5E8',
        'badge-new-text':    '#5A8A4A',
        'badge-sponsor-bg':  '#EAE6F5',
        'badge-sponsor-text':'#6B5FA8',

        // Filter chips
        chip:           '#F2F2F2',
        'chip-border':  '#D6D6D6',
        'chip-text':    '#606060',
        'chip-on':      '#E8E8E8',
        'chip-on-border':'#C4C4C4',
        'chip-on-text': '#1E3A36',

        // Accent / primary action (unchanged)
        'level-fill':  '#1E3A36',
      },
    },
  },
  plugins: [],
}

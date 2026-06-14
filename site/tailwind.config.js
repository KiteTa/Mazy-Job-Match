/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{ts,tsx}'],
  theme: {
    extend: {
      fontFamily: {
        serif: ['"DM Serif Display"', 'serif'],
      },
      colors: {
        // Core surfaces — teal-tinted (brand hue ≈ 185°)
        cream:     '#EEF6F5',   // body shell   (was warm #F7F3EC)
        parchment: '#F5FAFA',   // detail pane  (was warm #FDFAF6)
        'match-bg':'#DFF0EE',   // match card   (was warm #F0EBE2)
        sand:      '#C8D9D8',   // borders      (was warm #E5E0D8)

        // Header — keep existing teal
        header:        '#A8D8D0',
        'header-border':'#8ECAC0',

        // Row states
        'row-selected':'#D5ECEA',   // was #EDE7DC
        'row-hover':   '#E2EFED',   // was #F0EBE2

        // Tier indicators
        'tier-green':  '#8ABF78',
        'tier-amber':  '#C4A96A',
        'tier-gray':   '#9BBDBB',   // was warm #C0BAB2

        // Skill / JD highlight
        'skill-bg':    '#EDF5E8',
        'skill-text':  '#5A8A4A',
        'skill-border':'#B8D0CF',   // was warm #C4BDB2
        'jd-key':      '#2E6E78',   // was blue-gray #5A7A9A → teal-steel

        // New / Sponsor badges (semantic — kept)
        'badge-new-bg':      '#EDF5E8',
        'badge-new-text':    '#5A8A4A',
        'badge-sponsor-bg':  '#EAE6F5',
        'badge-sponsor-text':'#6B5FA8',

        // Filter chips
        chip:           '#E5F0EF',   // was warm #EFEBE3
        'chip-border':  '#BAD0CF',   // was warm #D9D4CB
        'chip-text':    '#4A7070',   // was warm #6B6560
        'chip-on':      '#CEEAE8',   // was warm #E8E2D8
        'chip-on-border':'#A8C8C6',  // was warm #C4BDB2
        'chip-on-text': '#1E3A36',   // was #3D3A36 — reuse forest green

        // Accent / primary action (unchanged)
        'level-fill':  '#1E3A36',
      },
    },
  },
  plugins: [],
}

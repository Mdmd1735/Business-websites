# UI/UX quality checklist (run on every site before publishing)

**Hero (first 5 seconds)**
- [ ] Business name, what it is, and where it is are clear without scrolling
- [ ] Real photo of the business (or a well-graded neutral image), with readable text over it (contrast ≥ 4.5:1)
- [ ] Primary CTA (WhatsApp / book / call) plus a secondary CTA
- [ ] Trust signal visible: Google rating + review count
- [ ] Headline is specific to this business, not generic

**Content**
- [ ] Prices, menu or services come from real sources; nothing invented
- [ ] Reviews are real (from Places), with name + time
- [ ] Hours, address, map, phone, WhatsApp, socials all correct and clickable (`tel:`, `wa.me`)
- [ ] Footer: "Preview concept prepared for …"; `noindex` meta present

**Visual**
- [ ] Theme fits the category (`playbook/THEMES.md`) and differs from other sites
- [ ] Max 2 font families + 1 accent colour; consistent spacing scale
- [ ] Images: object-fit cover, no stretched or pixelated images, ≤ 250 KB each, `loading="lazy"` below the fold, alt text
- [ ] No AI-look clichés (see THEMES.md)

**Interaction and accessibility**
- [ ] Tap targets ≥ 44px; visible `:focus-visible`; skip link; semantic landmarks
- [ ] Mobile menu works and closes on Esc/link click
- [ ] `prefers-reduced-motion` disables marquee, parallax and counters
- [ ] Animations use transform/opacity only; no layout shift on load

**Technical (automated by `playbook/qa.js`)**
- [ ] No horizontal overflow at 390px and 1440px
- [ ] No console errors
- [ ] Screenshots reviewed at both widths
- [ ] `<title>` + meta description + OG tags + schema.org LocalBusiness

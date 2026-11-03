(() => {
  const $ = (s, el = document) => el.querySelector(s);
  const $$ = (s, el = document) => [...el.querySelectorAll(s)];
  const reduce = matchMedia('(prefers-reduced-motion: reduce)').matches;

  // Hero entrance
  requestAnimationFrame(() => document.documentElement.classList.add('is-loaded'));

  // Nav state + floating WhatsApp
  const nav = $('#nav'), wa = $('.wa-float');
  const onScroll = () => {
    const y = scrollY;
    nav.classList.toggle('is-scrolled', y > 40);
    wa.classList.toggle('is-in', y > innerHeight * 0.6);
  };
  addEventListener('scroll', onScroll, { passive: true }); onScroll();

  // Mobile drawer
  const burger = $('.burger'), drawer = $('#drawer');
  const setDrawer = open => {
    burger.setAttribute('aria-expanded', open); drawer.hidden = !open;
    document.body.style.overflow = open ? 'hidden' : '';
  };
  burger.addEventListener('click', () => setDrawer(drawer.hidden));
  $$('a', drawer).forEach(a => a.addEventListener('click', () => setDrawer(false)));
  addEventListener('keydown', e => { if (e.key === 'Escape' && !drawer.hidden) setDrawer(false); });

  // Scroll reveals + counters
  const io = new IntersectionObserver(entries => entries.forEach(e => {
    if (!e.isIntersecting) return;
    e.target.classList.add('is-in'); io.unobserve(e.target);
    const n = $('[data-count]', e.target); if (n) count(n);
  }), { threshold: 0.15, rootMargin: '0px 0px -40px 0px' });
  $$('.reveal').forEach((el, i) => { el.style.transitionDelay = `${(i % 4) * 70}ms`; io.observe(el); });

  function count(el) {
    const end = parseFloat(el.dataset.count), dec = +(el.dataset.decimals || 0);
    const fmt = v => v.toLocaleString('en-US', { minimumFractionDigits: dec, maximumFractionDigits: dec });
    if (reduce) return (el.textContent = fmt(end));
    const t0 = performance.now(), dur = 1600;
    const tick = t => {
      const p = Math.min((t - t0) / dur, 1), k = 1 - Math.pow(1 - p, 4);
      el.textContent = fmt(end * k);
      if (p < 1) requestAnimationFrame(tick);
    };
    requestAnimationFrame(tick);
  }

  // Hero parallax
  const media = $('[data-parallax]');
  if (media && !reduce) addEventListener('scroll', () => {
    const y = scrollY; if (y < innerHeight) media.style.transform = `translate3d(0,${y * 0.25}px,0)`;
  }, { passive: true });

  // Magnetic buttons (pointer devices only)
  if (matchMedia('(hover:hover) and (pointer:fine)').matches && !reduce) {
    $$('.magnetic').forEach(b => {
      b.addEventListener('pointermove', e => {
        const r = b.getBoundingClientRect();
        b.style.transform = `translate(${(e.clientX - r.left - r.width / 2) * 0.18}px,${(e.clientY - r.top - r.height / 2) * 0.3}px)`;
      });
      b.addEventListener('pointerleave', () => (b.style.transform = ''));
    });
  }

  // Open-now status (Dubai time)
  const HOURS = { 0: [7, 21], 1: [5.5, 23], 2: [5.5, 23], 3: [5.5, 23], 4: [5.5, 23], 5: [5.5, 23], 6: [7, 21] };
  const dubai = new Date(new Date().toLocaleString('en-US', { timeZone: 'Asia/Dubai' }));
  const day = dubai.getDay(), now = dubai.getHours() + dubai.getMinutes() / 60;
  const [o, c] = HOURS[day], open = now >= o && now < c;
  const fmtH = h => { const H = Math.floor(h), m = Math.round((h - H) * 60); return `${((H + 11) % 12) + 1}${m ? ':' + String(m).padStart(2, '0') : ''} ${H < 12 ? 'AM' : 'PM'}`; };
  const st = $('[data-open-status]');
  if (st) {
    st.classList.add(open ? 'is-open' : 'is-closed');
    $('b', st).textContent = open ? `Open now · until ${fmtH(c)}` : `Closed · opens ${fmtH(now < o ? o : HOURS[(day + 1) % 7][0])}`;
  }
  $$('[data-hours] tr').forEach(tr => tr.classList.toggle('is-today', +tr.dataset.day === day));

  // Timetable
  const DAYS = ['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat'];
  const C = {
    s: ['Barbell Strength', 'Coach Karim', 'All levels'], h: ['HYROX Engine', 'Coach Lina', 'Intermediate'],
    b: ['Boxing Fundamentals', 'Coach Daniel', 'Beginner'], bx: ['Fight Club Conditioning', 'Coach Daniel', 'Advanced'],
    m: ['Mobility & Recovery', 'Coach Arjun', 'All levels'], w: ['Ladies Strength', 'Coach Lina', 'All levels'],
    o: ['Olympic Lifting', 'Coach Karim', 'Intermediate'], hx: ['HYROX Simulation', 'Coach Lina', 'Advanced']
  };
  const plan = {
    1: [['06:00', 's'], ['07:15', 'h'], ['10:00', 'w'], ['12:30', 'm'], ['18:00', 'o'], ['19:00', 'bx'], ['20:15', 'h']],
    2: [['06:00', 'h'], ['07:15', 'b'], ['10:00', 'w'], ['18:00', 's'], ['19:00', 'b'], ['20:15', 'm']],
    3: [['06:00', 's'], ['07:15', 'h'], ['10:00', 'w'], ['12:30', 'm'], ['18:00', 'o'], ['19:00', 'bx'], ['20:15', 'h']],
    4: [['06:00', 'h'], ['07:15', 'b'], ['10:00', 'w'], ['18:00', 's'], ['19:00', 'b'], ['20:15', 'm']],
    5: [['06:00', 's'], ['07:15', 'h'], ['17:30', 'w'], ['18:30', 'bx']],
    6: [['08:00', 'hx'], ['09:30', 'o'], ['11:00', 'w'], ['17:00', 'b']],
    0: [['08:00', 'm'], ['09:30', 's'], ['11:00', 'b']]
  };
  const tabs = $('[data-tabs]'), sched = $('[data-schedule]');
  const order = [1, 2, 3, 4, 5, 6, 0];
  const render = d => {
    $$('button', tabs).forEach(b => b.setAttribute('aria-selected', +b.dataset.d === d));
    sched.innerHTML = plan[d].map(([t, k], i) => {
      const [name, coach, lvl] = C[k];
      const spots = (t.charCodeAt(1) * 7 + i * 5 + d * 3) % 12; // deterministic demo availability
      return `<div class="slot" style="animation-delay:${i * 50}ms"><time>${t}</time><div><b>${name}</b><small>${coach} · 50 min</small></div><span class="lvl">${lvl}</span><span class="spots ${spots < 4 ? 'low' : ''}">${spots === 0 ? 'Waitlist' : spots + ' spots left'}</span></div>`;
    }).join('');
  };
  tabs.innerHTML = order.map(d => `<button role="tab" data-d="${d}" aria-selected="false">${DAYS[d]}${d === day ? '<span class="today">TODAY</span>' : ''}</button>`).join('');
  tabs.addEventListener('click', e => { const b = e.target.closest('button'); if (b) render(+b.dataset.d); });
  render(day);

  // Billing toggle
  $$('.billing button').forEach(btn => btn.addEventListener('click', () => {
    const p = btn.dataset.period;
    $$('.billing button').forEach(b => { const on = b === btn; b.classList.toggle('is-active', on); b.setAttribute('aria-pressed', on); });
    $$('.plan__price b[data-monthly]').forEach(b => {
      if (b.dataset.monthly === b.dataset.annual) return;
      b.style.opacity = 0;
      setTimeout(() => {
        b.textContent = b.dataset[p];
        const u = b.parentElement.querySelector('[data-unit]'); if (u) u.textContent = p === 'annual' ? '/year' : '/month';
        b.style.opacity = 1;
      }, 180);
    });
  }));

  // Seamless review marquee
  const track = $('.reviews__track');
  if (track && !reduce) $$('.review', track).forEach(r => { const c = r.cloneNode(true); c.setAttribute('aria-hidden', 'true'); track.appendChild(c); });

  $$('[data-year]').forEach(el => (el.textContent = new Date().getFullYear()));
})();

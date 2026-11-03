(() => {
  const $ = (s, el = document) => el.querySelector(s);
  const $$ = (s, el = document) => [...el.querySelectorAll(s)];
  const reduce = matchMedia('(prefers-reduced-motion: reduce)').matches;
  requestAnimationFrame(() => document.documentElement.classList.add('ready'));

  // Nav + WhatsApp button
  const nav = $('#nav'), fab = $('.wa-fab');
  const onScroll = () => { nav.classList.toggle('is-solid', scrollY > 30); fab.classList.toggle('on', scrollY > innerHeight * .7); };
  addEventListener('scroll', onScroll, { passive: true }); onScroll();

  // Drawer
  const burger = $('.burger'), drawer = $('#drawer');
  const setDrawer = open => { burger.setAttribute('aria-expanded', open); drawer.hidden = !open; document.body.style.overflow = open ? 'hidden' : ''; };
  burger.addEventListener('click', () => setDrawer(drawer.hidden));
  $$('a', drawer).forEach(a => a.addEventListener('click', () => setDrawer(false)));
  addEventListener('keydown', e => e.key === 'Escape' && !drawer.hidden && setDrawer(false));

  // Reveal on scroll
  const io = new IntersectionObserver(es => es.forEach(e => { if (e.isIntersecting) { e.target.classList.add('on'); io.unobserve(e.target); } }), { threshold: .12, rootMargin: '0px 0px -40px 0px' });
  $$('.rv').forEach((el, i) => { el.style.transitionDelay = `${(i % 3) * 80}ms`; io.observe(el); });

  // Dubai time
  const dxb = new Date(new Date().toLocaleString('en-US', { timeZone: 'Asia/Dubai' }));
  const day = dxb.getDay(), hour = dxb.getHours();
  const isOpen = day !== 0 || (hour >= 16 && hour < 22);
  const st = $('[data-status]');
  if (st) { st.classList.toggle('is-closed', !isOpen); $('b', st).textContent = isOpen ? (day === 0 ? 'Open now · until 10 PM' : 'Open 24 hours today') : (day === 0 && hour < 16 ? 'Opens 4 PM today' : 'Opens at midnight'); }
  $$('[data-hours] tr').forEach(tr => tr.classList.toggle('today', +tr.dataset.d === day));

  // Google Maps "popular times" (0–100), index = hour of day. Sunday hours are 4–10 PM.
  const BUSY = {
    0: [0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,10,14,18,22,23,25,0,0],
    1: [21,20,20,16,15,14,22,32,38,29,25,16,15,14,15,19,24,36,47,69,86,100,96,86],
    2: [55,40,25,17,23,28,30,32,24,21,20,22,20,18,12,9,11,21,42,67,86,94,89,73],
    3: [44,31,27,27,26,29,30,30,21,15,8,9,13,18,20,20,19,21,34,56,79,90,90,78],
    4: [53,36,26,24,20,20,23,20,16,17,17,17,16,16,19,19,20,30,49,72,98,97,92,72],
    5: [46,29,21,18,16,15,18,21,23,17,15,13,18,20,26,22,23,27,37,50,63,74,78,66],
    6: [40,23,17,20,14,17,19,21,21,18,15,16,18,20,18,18,18,23,34,44,45,44,41,38]
  };
  const NAMES = ['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat'];
  const FULL = ['Sunday', 'Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday'];
  const h12 = h => `${(h % 12) || 12} ${h < 12 ? 'AM' : 'PM'}`;
  const level = v => v === 0 ? 'closed' : v < 25 ? 'quiet' : v < 60 ? 'moderate' : 'busy';

  // Hero live card
  const now = BUSY[day][hour];
  const liveText = $('[data-live-text]');
  if (liveText) {
    liveText.textContent = !isOpen ? 'Closed right now' :
      now < 25 ? 'Usually quiet now. Good time to train.' : now < 60 ? 'Usually a steady crowd now.' : 'Peak hours. Expect a buzz.';
    const lb = $('[data-live-bars]');
    const from = Math.max(0, Math.min(hour - 5, 12));
    lb.innerHTML = BUSY[day].slice(from, from + 12).map((v, i) => `<i class="${from + i === hour ? 'now' : ''}" style="height:0"></i>`).join('');
    setTimeout(() => $$('i', lb).forEach((b, i) => (b.style.height = Math.max(5, BUSY[day][from + i]) + '%')), 700);
  }

  // Crowd chart
  const daysEl = $('[data-days]'), bars = $('[data-bars]'), sum = $('[data-crowd-sum]');
  const order = [1, 2, 3, 4, 5, 6, 0];
  daysEl.innerHTML = order.map(d => `<button role="tab" data-d="${d}" aria-selected="false">${NAMES[d]}</button>`).join('');
  bars.innerHTML = Array.from({ length: 24 }, () => '<i></i>').join('');
  const quietWindow = d => {
    let best = null, cur = null;
    BUSY[d].forEach((v, h) => {
      if (v > 0 && v < 25 && h >= 6) { cur = cur ? { s: cur.s, e: h } : { s: h, e: h }; if (!best || cur.e - cur.s > best.e - best.s) best = { ...cur }; }
      else cur = null;
    });
    return best;
  };
  const render = d => {
    $$('button', daysEl).forEach(b => b.setAttribute('aria-selected', +b.dataset.d === d));
    $$('i', bars).forEach((b, h) => {
      const v = BUSY[d][h];
      b.className = (d === day && h === hour ? 'now' : '') + ' ' + (v >= 70 ? 'busy' : v > 0 && v < 25 ? 'quiet' : '');
      b.style.height = (reduce ? v : 0) + '%';
      b.title = `${h12(h)}: ${level(v)}`;
      if (!reduce) setTimeout(() => (b.style.height = Math.max(v ? 4 : 1, v) + '%'), 20 + h * 18);
    });
    const peak = BUSY[d].indexOf(Math.max(...BUSY[d]));
    const q = quietWindow(d);
    sum.innerHTML = d === 0 ? `<b>Sunday</b> is short hours (4 to 10 PM) and the quietest day of the week.` :
      `<b>${FULL[d]}</b>: busiest around <b>${h12(peak)}</b>.` + (q ? ` Quietest from <b>${h12(q.s)}</b> to <b>${h12(q.e + 1)}</b>.` : '');
    bars.setAttribute('aria-label', `${FULL[d]} busyness by hour. Peak at ${h12(peak)}.`);
  };
  daysEl.addEventListener('click', e => { const b = e.target.closest('button'); if (b) render(+b.dataset.d); });
  const chartIO = new IntersectionObserver(es => { if (es[0].isIntersecting) { render(day); chartIO.disconnect(); } }, { threshold: .3 });
  chartIO.observe(bars);
})();

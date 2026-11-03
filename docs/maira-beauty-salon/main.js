(() => {
  const S = window.SITE || {};
  const $ = (s, el = document) => el.querySelector(s);
  const $$ = (s, el = document) => [...el.querySelectorAll(s)];
  const reduce = matchMedia('(prefers-reduced-motion: reduce)').matches;
  requestAnimationFrame(() => document.documentElement.classList.add('ready'));

  const nav = $('#nav'), fab = $('.wa-fab');
  const onScroll = () => { nav.classList.toggle('is-solid', scrollY > 30); fab && fab.classList.toggle('on', scrollY > innerHeight * .7); };
  addEventListener('scroll', onScroll, { passive: true }); onScroll();

  const burger = $('.burger'), drawer = $('#drawer');
  const setDrawer = open => { burger.setAttribute('aria-expanded', open); drawer.hidden = !open; document.body.style.overflow = open ? 'hidden' : ''; };
  burger.addEventListener('click', () => setDrawer(drawer.hidden));
  $$('a', drawer).forEach(a => a.addEventListener('click', () => setDrawer(false)));
  addEventListener('keydown', e => e.key === 'Escape' && !drawer.hidden && setDrawer(false));

  const io = new IntersectionObserver(es => es.forEach(e => { if (e.isIntersecting) { e.target.classList.add('on'); io.unobserve(e.target); } }), { threshold: .12, rootMargin: '0px 0px -40px 0px' });
  $$('.rv').forEach((el, i) => { el.style.transitionDelay = `${(i % 3) * 80}ms`; io.observe(el); });

  // Dubai clock
  const dxb = new Date(new Date().toLocaleString('en-US', { timeZone: 'Asia/Dubai' }));
  const day = dxb.getDay(), hour = dxb.getHours(), mins = hour * 60 + dxb.getMinutes();
  const h12 = m => { const h = Math.floor(m / 60) % 24, mm = m % 60; return `${(h % 12) || 12}${mm ? ':' + String(mm).padStart(2, '0') : ''} ${h < 12 ? 'AM' : 'PM'}`; };

  // Open status. S.hours[d] = [[openMin, closeMin], ...]; close may exceed 1440 (past midnight)
  let isOpen = true;
  if (S.hours) {
    const prev = (day + 6) % 7;
    const inRange = (d, m) => (S.hours[d] || []).some(([o, c]) => m >= o && m < c);
    const openSpan = (S.hours[day] || []).find(([o, c]) => mins >= o && mins < c) || (S.hours[prev] || []).find(([o, c]) => c > 1440 && mins + 1440 < c);
    isOpen = !!openSpan || inRange(day, mins);
    const st = $('[data-status]');
    if (st) {
      let txt;
      if (openSpan) txt = openSpan[1] - openSpan[0] >= 1440 ? 'Open 24 hours' : `Open now · until ${h12(openSpan[1] % 1440 === openSpan[1] ? openSpan[1] : openSpan[1] - 1440)}`;
      else {
        const next = (S.hours[day] || []).find(([o]) => o > mins);
        txt = next ? `Closed · opens ${h12(next[0])}` : (() => { for (let i = 1; i < 8; i++) { const d = (day + i) % 7; if ((S.hours[d] || []).length) return `Closed · opens ${['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat'][d]} ${h12(S.hours[d][0][0])}`; } return 'Closed'; })();
      }
      st.classList.toggle('is-closed', !openSpan); $('b', st).textContent = txt;
    }
  }
  $$('[data-hours] tr').forEach(tr => tr.classList.toggle('today', +tr.dataset.d === day));

  // Menu tabs
  $$('.menu').forEach(m => {
    const tabs = $$('.menu__tabs button', m);
    tabs.forEach(t => t.addEventListener('click', () => {
      tabs.forEach(x => x.setAttribute('aria-selected', x === t));
      $$('.menu__panel', m).forEach(p => (p.hidden = p.dataset.panel !== t.dataset.tab));
    }));
  });

  // Popular times
  const B = S.busy; if (!B) return;
  const NAMES = ['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat'], FULL = ['Sunday', 'Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday'];
  const hh = h => `${(h % 12) || 12} ${h < 12 ? 'AM' : 'PM'}`;
  const now = (B[day] || [])[hour] || 0;
  const lt = $('[data-live-text]');
  if (lt) {
    lt.textContent = !isOpen ? 'Closed right now' : now < 25 ? 'Usually quiet now. Good time to come in.' : now < 60 ? 'Usually steady right now.' : 'Peak hours right now.';
    const lb = $('[data-live-bars]'), from = Math.max(0, Math.min(hour - 5, 12));
    lb.innerHTML = B[day].slice(from, from + 12).map((v, i) => `<i class="${from + i === hour ? 'now' : ''}"></i>`).join('');
    setTimeout(() => $$('i', lb).forEach((b, i) => (b.style.height = Math.max(5, B[day][from + i]) + '%')), 700);
  }
  const daysEl = $('[data-days]'), bars = $('[data-bars]'), sum = $('[data-crowd-sum]');
  if (!bars) return;
  const order = [1, 2, 3, 4, 5, 6, 0].filter(d => B[d] && B[d].some(v => v > 0));
  daysEl.innerHTML = order.map(d => `<button role="tab" data-d="${d}" aria-selected="false">${NAMES[d]}</button>`).join('');
  bars.innerHTML = Array.from({ length: 24 }, () => '<i></i>').join('');
  const quiet = d => { let best = null, cur = null; B[d].forEach((v, h) => { if (v > 0 && v < 30 && h >= 7) { cur = cur ? { s: cur.s, e: h } : { s: h, e: h }; if (!best || cur.e - cur.s > best.e - best.s) best = { ...cur }; } else cur = null; }); return best; };
  const render = d => {
    $$('button', daysEl).forEach(b => b.setAttribute('aria-selected', +b.dataset.d === d));
    $$('i', bars).forEach((b, h) => {
      const v = B[d][h];
      b.className = (d === day && h === hour ? 'now ' : '') + (v >= 70 ? 'busy' : v > 0 && v < 30 ? 'quiet' : '');
      b.style.height = reduce ? v + '%' : '0%';
      if (!reduce) setTimeout(() => (b.style.height = Math.max(v ? 4 : 1, v) + '%'), 20 + h * 18);
    });
    const peak = B[d].indexOf(Math.max(...B[d])), q = quiet(d);
    sum.innerHTML = `<b>${FULL[d]}</b>: busiest around <b>${hh(peak)}</b>.` + (q && q.e > q.s ? ` Quietest from <b>${hh(q.s)}</b> to <b>${hh(q.e + 1)}</b>.` : '');
    bars.setAttribute('aria-label', `${FULL[d]} busyness by hour. Peak at ${hh(peak)}.`);
  };
  daysEl.addEventListener('click', e => { const b = e.target.closest('button'); if (b) render(+b.dataset.d); });
  const cio = new IntersectionObserver(es => { if (es[0].isIntersecting) { render(order.includes(day) ? day : order[0]); cio.disconnect(); } }, { threshold: .3 });
  cio.observe(bars);
})();

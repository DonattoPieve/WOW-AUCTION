// Gráfico de linha em SVG puro. Uma biblioteca de gráficos resolveria o mesmo
// problema com ~200 KB a mais: aqui o desenho inteiro são duas funções de
// escala e um <polyline>.
const W = 800, H = 260, PL = 56, PR = 12, PT = 16, PB = 26;

const fmtOuro = (n) =>
  n >= 1e6 ? (n / 1e6).toFixed(2) + 'M' : n >= 1e4 ? (n / 1e3).toFixed(1) + 'K' : n.toFixed(2);

export function desenharGrafico(el, points, { aoPassar } = {}) {
  if (!points.length) {
    el.innerHTML = '<p class="muted">Sem dados para esta faixa.</p>';
    return;
  }

  const vs = points.map((p) => p.value);
  const min = Math.min(...vs), max = Math.max(...vs), span = max - min || 1;
  // índice -> coluna, valor -> linha (invertido: no SVG o Y cresce para baixo)
  const x = (i) => PL + (i * (W - PL - PR)) / (points.length - 1 || 1);
  const y = (v) => PT + (1 - (v - min) / span) * (H - PT - PB);

  const linha = points.map((p, i) => `${x(i).toFixed(1)},${y(p.value).toFixed(1)}`).join(' ');

  const grade = [0, 1, 2, 3, 4]
    .map((k) => {
      const v = min + (span * k) / 4;
      return `<line x1="${PL}" x2="${W - PR}" y1="${y(v)}" y2="${y(v)}" class="grade"/>
              <text x="${PL - 8}" y="${y(v) + 4}" text-anchor="end">${fmtOuro(v)}</text>`;
    })
    .join('');

  const datas = [0, 0.5, 1]
    .map((k, n) => {
      const i = Math.round(k * (points.length - 1));
      const d = new Date(points[i].ts * 1000).toLocaleDateString('pt-BR');
      return `<text x="${x(i)}" y="${H - 6}" text-anchor="${['start', 'middle', 'end'][n]}">${d}</text>`;
    })
    .join('');

  el.innerHTML = `
    <svg viewBox="0 0 ${W} ${H}" role="img" aria-label="Histórico de preço">
      <defs><linearGradient id="fade" x1="0" y1="0" x2="0" y2="1">
        <stop offset="0" stop-color="var(--accent)" stop-opacity=".35"/>
        <stop offset="1" stop-color="var(--accent)" stop-opacity="0"/>
      </linearGradient></defs>
      ${grade}${datas}
      <polygon points="${PL},${H - PB} ${linha} ${W - PR},${H - PB}" fill="url(#fade)"/>
      <polyline points="${linha}" class="linha"/>
      <line class="cursor" y1="${PT}" y2="${H - PB}" style="display:none"/>
      <circle class="ponto" r="4" style="display:none"/>
    </svg>
    <div class="dica"></div>`;

  const svg = el.querySelector('svg');
  const cursor = el.querySelector('.cursor');
  const dot = el.querySelector('.ponto');
  const tip = el.querySelector('.dica');

  const mover = (clientX) => {
    const r = svg.getBoundingClientRect();
    const px = ((clientX - r.left) / r.width) * W;
    const i = Math.max(0, Math.min(points.length - 1, Math.round(((px - PL) / (W - PL - PR)) * (points.length - 1))));
    const p = points[i], cx = x(i), cy = y(p.value);

    cursor.style.display = dot.style.display = '';
    cursor.setAttribute('x1', cx); cursor.setAttribute('x2', cx);
    dot.setAttribute('cx', cx); dot.setAttribute('cy', cy);
    tip.style.display = 'block';
    tip.style.left = `clamp(60px, ${(cx / W) * 100}%, calc(100% - 60px))`;
    tip.innerHTML = `<b>${fmtOuro(p.value)} g</b><br>${new Date(p.ts * 1000).toLocaleString('pt-BR')}<br>Qtd: ${p.quantity.toLocaleString('pt-BR')}`;
    aoPassar?.(p);
  };

  svg.addEventListener('mousemove', (e) => mover(e.clientX));
  svg.addEventListener('touchmove', (e) => mover(e.touches[0].clientX), { passive: true });
  svg.addEventListener('mouseleave', () => {
    cursor.style.display = dot.style.display = tip.style.display = 'none';
  });
}

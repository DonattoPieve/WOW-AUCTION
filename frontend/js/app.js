import { api } from './api.js';
import { desenharGrafico } from './grafico.js';
import { desenharMapaCalor } from './mapa-calor.js';

const app = document.querySelector('#app');
const RANGES = ['daily', 'weekly', 'monthly', 'quarter', 'half-year', 'year'];
const ROTULO = { daily: 'Dia', weekly: 'Semana', monthly: 'Mês', quarter: 'Trimestre', 'half-year': 'Semestre', year: 'Ano' };

const state = { region: 'us', range: 'weekly', q: '', category: '', sort: 'name' };

const fmt = (n) => (n >= 1e6 ? (n / 1e6).toFixed(2) + 'M' : n >= 1e4 ? (n / 1e3).toFixed(1) + 'K' : Number(n).toFixed(2));
const int = (n) => Number(n).toLocaleString('pt-BR');
const pct = (n) => `<span class="${n >= 0 ? 'alta' : 'baixa'}">${n >= 0 ? '+' : ''}${Number(n).toFixed(2)}%</span>`;
const erro = (e) => `<p class="erro">Não foi possível carregar: ${e.message}</p>`;

// ---------- Lista ----------
async function renderList() {
  app.innerHTML = '<p class="muted">Carregando...</p>';
  try {
    const [cats, itens] = await Promise.all([api.categories(), api.items(state)]);
    app.innerHTML = `
      <h1>Itens</h1>
      <p class="muted">Commodities da região ${state.region.toUpperCase()}.</p>
      <div class="filtros">
        <input id="q" placeholder="Buscar item..." value="${state.q}" aria-label="Buscar item">
        <select id="category" aria-label="Categoria"><option value="">Todas as categorias</option>
          ${cats.map((c) => `<option ${c === state.category ? 'selected' : ''}>${c}</option>`).join('')}</select>
        <select id="sort" aria-label="Ordenar por">
          ${[['name', 'Nome'], ['value', 'Maior valor'], ['change', 'Maior alta'], ['quantity', 'Maior quantidade']]
            .map(([k, l]) => `<option value="${k}" ${k === state.sort ? 'selected' : ''}>${l}</option>`).join('')}</select>
      </div>
      <table>
        <thead><tr><th>Item</th><th>Categoria</th><th class="r">Valor</th><th class="r">24h</th><th class="r">Quantidade</th></tr></thead>
        <tbody>${linhas(itens)}</tbody>
      </table>`;

    for (const id of ['q', 'category', 'sort']) {
      const el = document.querySelector('#' + id);
      el.oninput = debounce(() => { state[id] = el.value; atualizarLinhas(); }, 250);
    }
  } catch (e) {
    app.innerHTML = erro(e);
  }
}

const linhas = (itens) =>
  itens.map((i) => `
    <tr tabindex="0" data-id="${i.id}">
      <td><span class="q-${i.quality.toLowerCase()}">${i.name}</span></td>
      <td class="muted">${i.category}</td>
      <td class="r num">${fmt(i.value)} g</td>
      <td class="r num">${pct(i.change_pct)}</td>
      <td class="r num">${int(i.quantity)}</td>
    </tr>`).join('') || '<tr><td colspan="5" class="muted">Nenhum item encontrado.</td></tr>';

async function atualizarLinhas() {
  const tbody = document.querySelector('tbody');
  if (tbody) tbody.innerHTML = linhas(await api.items(state));
}

// ---------- Detalhe ----------
async function renderItem(id) {
  app.innerHTML = '<p class="muted">Carregando...</p>';
  try {
    const [d, serie] = await Promise.all([api.item(id, state.region), api.series(id, state.region, state.range)]);
    const outra = state.region === 'us' ? 'eu' : 'us';
    const { item, daily, averages } = d;

    app.innerHTML = `
      <a href="#" class="voltar muted">← Itens</a>
      <header class="item">
        <div class="icone" aria-hidden="true">${item.name[0]}</div>
        <div>
          <h1><a class="q-${item.quality.toLowerCase()}" href="https://www.wowhead.com/item=${item.id}"
                 target="_blank" rel="noopener">${item.name}</a></h1>
          <p class="muted">${item.quality} / ${item.category}</p>
        </div>
      </header>
      <p class="muted">Atualizado: ${daily.ts ? new Date(daily.ts * 1000).toLocaleString('pt-BR') : '—'}</p>

      <div class="cards">
        <section class="card">
          <h2>Valor atual</h2>
          <div class="grande">${fmt(daily.value)} g</div>${pct(daily.change_pct)}
          <p class="muted">${daily.change >= 0 ? 'Valor subindo hoje' : 'Valor caindo hoje'} · Qtd: ${int(daily.quantity)}</p>
        </section>
        <section class="card">
          <h2>Estatísticas do dia</h2>
          <dl>
            <dt>Valor de mercado</dt><dd>${fmt(daily.market_value)}</dd>
            <dt>Variação</dt><dd>${daily.change.toFixed(2)} (${pct(daily.change_pct)})</dd>
            <dt>Vendas</dt><dd>${int(daily.sales)}</dd>
            <dt>Volume</dt><dd>${fmt(daily.volume)}</dd>
          </dl>
        </section>
        <section class="card">
          <h2>Médias</h2>
          <table class="mini">
            <tr><th></th><th class="r">${state.region.toUpperCase()}</th><th class="r">${outra.toUpperCase()}</th></tr>
            ${[['Diária', 'daily'], ['Semanal', 'weekly'], ['Mensal', 'monthly']].map(([rot, k]) =>
              `<tr><td>${rot}</td><td class="r num">${fmt(averages[state.region][k])}</td><td class="r num">${fmt(averages[outra][k])}</td></tr>`).join('')}
          </table>
        </section>
      </div>

      <section class="card">
        <h2>Tendência de mercado</h2>
        <div class="abas">${RANGES.map((r) =>
          `<button class="${r === state.range ? 'on' : ''}" data-range="${r}">${ROTULO[r]}</button>`).join('')}</div>
        <div class="grafico" id="grafico"></div>
      </section>

      <div class="cards duas">
        <section class="card"><h2>Heatmap semanal (valor)</h2><div id="mapa-value"></div></section>
        <section class="card"><h2>Heatmap semanal (quantidade)</h2><div id="mapa-quantity"></div></section>
      </div>`;

    desenharGrafico(document.querySelector('#grafico'), serie.points);

    for (const b of document.querySelectorAll('.abas button')) {
      b.onclick = async () => {
        state.range = b.dataset.range;
        for (const o of document.querySelectorAll('.abas button')) o.classList.toggle('on', o === b);
        const s = await api.series(id, state.region, state.range);
        desenharGrafico(document.querySelector('#grafico'), s.points);
      };
    }

    for (const campo of ['value', 'quantity']) {
      api.heatmap(id, state.region, campo)
         .then((h) => desenharMapaCalor(document.querySelector('#mapa-' + campo), h.grid,
                                       { rotulo: `média de ${h.weeks} semanas` }));
    }
  } catch (e) {
    app.innerHTML = erro(e);
  }
}

// ---------- Rotas ----------
function debounce(fn, ms) {
  let t;
  return (...a) => { clearTimeout(t); t = setTimeout(() => fn(...a), ms); };
}

function route() {
  const [, pagina, id] = location.hash.split('/');
  return pagina === 'item' ? renderItem(Number(id)) : renderList();
}

app.addEventListener('click', (e) => {
  const tr = e.target.closest('tr[data-id]');
  if (tr) location.hash = `#/item/${tr.dataset.id}`;
});
app.addEventListener('keydown', (e) => {
  const tr = e.target.closest('tr[data-id]');
  if (tr && e.key === 'Enter') location.hash = `#/item/${tr.dataset.id}`;
});

document.querySelector('#regiao').onchange = (e) => {
  state.region = e.target.value;
  route();
};

// Tema: o atributo no <html> manda, e o localStorage lembra. O script inline do
// index.html aplica o valor salvo antes da primeira pintura.
document.querySelector('#tema').onclick = () => {
  const html = document.documentElement;
  const escuro = html.dataset.theme
    ? html.dataset.theme === 'dark'
    : matchMedia('(prefers-color-scheme: dark)').matches;

  html.dataset.theme = escuro ? 'light' : 'dark';
  try {
    localStorage.setItem('tema', html.dataset.theme);
  } catch { /* modo privado: vale só para esta aba */ }
};
window.addEventListener('hashchange', route);
route();

// A Blizzard publica um snapshot novo por hora; recarregar mais rápido que isso
// só gastaria requisição para receber o mesmo número de volta.
setInterval(route, 60 * 60 * 1000);

import { api } from "./api.js";
import { SERIES, desenharGrafico } from "./grafico.js";
import { desenharMapaCalor } from "./mapa-calor.js";

const app = document.querySelector("#app");
const RANGES = ["daily", "weekly", "monthly", "quarter", "half-year", "year"];
const ROTULO = {
  daily: "Daily",
  weekly: "Weekly",
  monthly: "Monthly",
  quarter: "Quarter",
  "half-year": "Half Year",
  year: "Year",
};

// O realm é fixo (Area 52 / US). Commodities têm mercado único por região, então
// não há seletor: ver backend/app/config.py para o porquê.
const state = {
  range: "daily",
  category: "",
  sort: "name",
  series: new Set(["value", "min_buyout", "quantity"]),
  soFavoritos: false,
};

// ---------------------------------------------------------------- utilidades

const fmt = (n) =>
  n >= 1e6
    ? (n / 1e6).toFixed(2) + "M"
    : n >= 1e4
      ? (n / 1e3).toFixed(1) + "K"
      : Number(n).toFixed(2);
const int = (n) => Number(n).toLocaleString("pt-BR");
const pct = (n) =>
  `<span class="${n >= 0 ? "alta" : "baixa"}">${n >= 0 ? "+" : ""}${Number(n).toFixed(2)}%</span>`;
const erro = (e) =>
  `<p class="erro">Não foi possível carregar: ${e.message}</p>`;
const escapar = (t) =>
  String(t).replace(
    /[<>&"]/g,
    (c) => ({ "<": "&lt;", ">": "&gt;", "&": "&amp;", '"': "&quot;" })[c],
  );

const exibido = (i) => i.name_ptbr || i.name;

// O nome em inglês fica visível de propósito: é o que aparece na Auction House
// do jogo e o que a pessoa digita para procurar.
const nome = (i) =>
  i.name_ptbr && i.name_ptbr !== i.name
    ? `${escapar(i.name_ptbr)} <span class="nome-en">${escapar(i.name)}</span>`
    : escapar(i.name);

/** Ícone do item, ou um quadrado com a inicial quando a API não tem um. */
const icone = (i, tam = 28) =>
  i.icon
    ? `<img class="icone-item" width="${tam}" height="${tam}" loading="lazy" alt="" src="${escapar(i.icon)}">`
    : `<span class="icone-item vazio" style="width:${tam}px;height:${tam}px" aria-hidden="true">${escapar(exibido(i)[0])}</span>`;

function debounce(fn, ms) {
  let t;
  return (...a) => {
    clearTimeout(t);
    t = setTimeout(() => fn(...a), ms);
  };
}

// ---------------------------------------------------------------- favoritos
// Ficam no navegador porque o projeto não tem login (ver docs/arquitetura.md).
// Consequência aceita: são por navegador, não seguem a pessoa para outro
// dispositivo. Trocar isso exigiria conta, e conta é bem mais que uma tabela.
const CHAVE_FAV = "favoritos";

function lerFavoritos() {
  try {
    return new Set(JSON.parse(localStorage.getItem(CHAVE_FAV) || "[]"));
  } catch {
    return new Set(); // modo privado ou dado corrompido: começa vazio
  }
}

const favoritos = lerFavoritos();

function alternarFavorito(id) {
  favoritos.has(id) ? favoritos.delete(id) : favoritos.add(id);
  try {
    localStorage.setItem(CHAVE_FAV, JSON.stringify([...favoritos]));
  } catch {
    /* sem persistência neste navegador; a marcação vale para esta sessão */
  }
}

const estrela = (id) => `
  <button type="button" class="favorito ${favoritos.has(id) ? "on" : ""}" data-fav="${id}"
          aria-pressed="${favoritos.has(id)}"
          title="${favoritos.has(id) ? "Remover dos favoritos" : "Salvar nos favoritos"}">
    ${favoritos.has(id) ? "★" : "☆"}
  </button>`;

// ---------------------------------------------------------------- busca
// Dropdown com ícone e nome, como a busca do próprio jogo: a pessoa reconhece
// o item pela arte antes de ler o nome.

async function buscar(termo) {
  const caixa = document.querySelector("#resultados");
  if (!caixa) return;

  if (termo.trim().length < 2) {
    caixa.hidden = true;
    caixa.innerHTML = "";
    return;
  }

  try {
    const itens = await api.items({ q: termo, limit: 10 });
    caixa.hidden = false;
    caixa.innerHTML = itens.length
      ? `<p class="titulo-lista">Itens</p>` +
        itens
          .map(
            (i) => `
          <button type="button" class="resultado" data-ir="${i.id}">
            ${icone(i, 24)}
            <span class="q-${i.quality.toLowerCase()}">${nome(i)}</span>
            <span class="valor-resultado">${fmt(i.value)} g</span>
          </button>`,
          )
          .join("")
      : '<p class="titulo-lista">Nada encontrado</p>';

    for (const b of caixa.querySelectorAll(".resultado")) {
      b.onclick = () => {
        caixa.hidden = true;
        document.querySelector("#busca").value = "";
        location.hash = `#/item/${b.dataset.ir}`;
      };
    }
  } catch {
    caixa.hidden = true;
  }
}

// ---------------------------------------------------------------- lista

async function renderLista() {
  app.innerHTML = '<p class="muted">Carregando...</p>';
  try {
    const [cats, itens] = await Promise.all([
      api.categories(),
      api.items(state),
    ]);
    app.innerHTML = `
      <h1>Itens</h1>
      <p class="muted">Commodities do mercado da região, vistas de ${realmTexto()}.</p>
      <div class="filtros">
        <select id="category" aria-label="Categoria">
          <option value="">Todas as categorias</option>
          ${cats.map((c) => `<option ${c === state.category ? "selected" : ""}>${escapar(c)}</option>`).join("")}
        </select>
        <select id="sort" aria-label="Ordenar por">
          ${[
            ["name", "Nome"],
            ["value", "Maior valor"],
            ["change", "Maior alta"],
            ["quantity", "Maior quantidade"],
          ]
            .map(
              ([k, l]) =>
                `<option value="${k}" ${k === state.sort ? "selected" : ""}>${l}</option>`,
            )
            .join("")}
        </select>
        <button type="button" id="so-favoritos" class="alternador ${state.soFavoritos ? "on" : ""}"
                aria-pressed="${state.soFavoritos}">★ Só favoritos</button>
      </div>
      <table>
        <thead>
          <tr>
            <th class="col-fav"><span class="sr-only">Favorito</span></th>
            <th>Item</th><th>Categoria</th>
            <th class="r">Valor</th><th class="r">24h</th><th class="r">Quantidade</th>
          </tr>
        </thead>
        <tbody>${linhas(itens)}</tbody>
      </table>`;

    for (const id of ["category", "sort"]) {
      const el = document.querySelector("#" + id);
      el.onchange = () => {
        state[id] = el.value;
        atualizarLinhas();
      };
    }
    document.querySelector("#so-favoritos").onclick = () => {
      state.soFavoritos = !state.soFavoritos;
      renderLista();
    };
  } catch (e) {
    app.innerHTML = erro(e);
  }
}

function linhas(itens) {
  const lista = state.soFavoritos
    ? itens.filter((i) => favoritos.has(i.id))
    : itens;
  if (!lista.length) {
    const aviso = state.soFavoritos
      ? "Nenhum favorito ainda. Clique na estrela de um item para salvá-lo."
      : "Nenhum item encontrado.";
    return `<tr><td colspan="6" class="muted">${aviso}</td></tr>`;
  }

  return lista
    .map(
      (i) => `
    <tr data-id="${i.id}" tabindex="0">
      <td class="col-fav">${estrela(i.id)}</td>
      <td class="celula-item">${icone(i)}<span class="q-${i.quality.toLowerCase()}">${nome(i)}</span></td>
      <td class="muted">${escapar(i.category)}</td>
      <td class="r">${fmt(i.value)} g</td>
      <td class="r">${pct(i.change_pct)}</td>
      <td class="r">${int(i.quantity)}</td>
    </tr>`,
    )
    .join("");
}

async function atualizarLinhas() {
  const tbody = document.querySelector("tbody");
  if (tbody) tbody.innerHTML = linhas(await api.items(state));
}

// ---------------------------------------------------------------- detalhe

async function renderItem(id) {
  app.innerHTML = '<p class="muted">Carregando...</p>';
  try {
    const [d, serie] = await Promise.all([
      api.item(id),
      api.series(id, state.range),
    ]);
    const { item, daily, averages } = d;

    app.innerHTML = `
      <a href="#" class="voltar muted">← Itens</a>
      <header class="item">
        ${icone(item, 52)}
        <div class="titulo-item">
          <h1>
            <a class="q-${item.quality.toLowerCase()}" href="https://www.wowhead.com/item=${item.id}"
               target="_blank" rel="noopener">${escapar(exibido(item))}</a>
          </h1>
          ${item.name_ptbr && item.name_ptbr !== item.name ? `<p class="nome-en">${escapar(item.name)}</p>` : ""}
          <p class="muted">${escapar(item.quality)} / ${escapar(item.category)}</p>
        </div>
        ${estrela(item.id)}
      </header>
      <p class="muted">
        ${realmTexto()} ·
        atualizado ${daily.ts ? new Date(daily.ts * 1000).toLocaleString("pt-BR") : "—"}
      </p>

      <div class="cards">
        <section class="card">
          <h2>Valor atual</h2>
          <div class="grande">${fmt(daily.value)} g</div>${pct(daily.change_pct)}
          <p class="muted">
            ${daily.change >= 0 ? "Valor subindo hoje" : "Valor caindo hoje"} · Qtd: ${int(daily.quantity)}
          </p>
        </section>
        <section class="card">
          <h2>Estatísticas do dia</h2>
          <dl>
            <dt>Valor de mercado</dt><dd>${fmt(daily.market_value)}</dd>
            <dt>Min buyout</dt><dd>${daily.min_buyout ? fmt(daily.min_buyout) : "—"}</dd>
            <dt>Variação</dt><dd>${daily.change.toFixed(2)} (${pct(daily.change_pct)})</dd>
            <dt>Vendas</dt><dd>${int(daily.sales)}</dd>
            <dt>Volume</dt><dd>${fmt(daily.volume)}</dd>
          </dl>
        </section>
        <section class="card">
          <h2>Médias</h2>
          <dl>
            <dt>Diária</dt><dd>${fmt(averages.us.daily)}</dd>
            <dt>Semanal</dt><dd>${fmt(averages.us.weekly)}</dd>
            <dt>Mensal</dt><dd>${fmt(averages.us.monthly)}</dd>
          </dl>
        </section>
      </div>

      <section class="card">
        <div class="cabecalho-grafico">
          <h2>Market Trend</h2>
          <div class="abas">
            ${RANGES.map(
              (r) =>
                `<button type="button" class="${r === state.range ? "on" : ""}" data-range="${r}">${ROTULO[r]}</button>`,
            ).join("")}
          </div>
        </div>
        <div id="grafico"></div>
      </section>

      <div class="cards duas">
        <section class="card"><h2>Heatmap semanal (valor)</h2><div id="calor-value"></div></section>
        <section class="card"><h2>Heatmap semanal (quantidade)</h2><div id="calor-quantity"></div></section>
      </div>`;

    let pontos = serie.points;
    const pintar = () =>
      desenharGrafico(
        document.querySelector("#grafico"),
        pontos,
        state.series,
        (chave) => {
          // Nunca deixa ficar sem nenhuma série: desligar a última não mostraria
          // nada e o clique pareceria ter quebrado a tela.
          if (state.series.has(chave) && state.series.size === 1) return;
          state.series.has(chave)
            ? state.series.delete(chave)
            : state.series.add(chave);
          pintar();
        },
      );
    pintar();

    for (const b of document.querySelectorAll(".abas button")) {
      b.onclick = async () => {
        state.range = b.dataset.range;
        for (const o of document.querySelectorAll(".abas button"))
          o.classList.toggle("on", o === b);
        pontos = (await api.series(id, state.range)).points;
        pintar();
      };
    }

    for (const campo of ["value", "quantity"]) {
      api
        .heatmap(id, campo)
        .then((h) =>
          desenharMapaCalor(document.querySelector("#calor-" + campo), h.grid),
        )
        .catch(() => {});
    }
  } catch (e) {
    app.innerHTML = erro(e);
  }
}

// ---------------------------------------------------------------- realm

let realm = null;
const realmTexto = () =>
  realm ? `${realm.nome} (${realm.region.toUpperCase()})` : "";

// ---------------------------------------------------------------- rotas

function route() {
  const [, pagina, id] = location.hash.split("/");
  return pagina === "item" ? renderItem(Number(id)) : renderLista();
}

app.addEventListener("click", (e) => {
  const fav = e.target.closest("[data-fav]");
  if (fav) {
    e.stopPropagation();
    alternarFavorito(Number(fav.dataset.fav));
    return state.soFavoritos ? renderLista() : route();
  }
  const linha = e.target.closest("tr[data-id]");
  if (linha) location.hash = `#/item/${linha.dataset.id}`;
});

app.addEventListener("keydown", (e) => {
  const linha = e.target.closest("tr[data-id]");
  if (linha && e.key === "Enter") location.hash = `#/item/${linha.dataset.id}`;
});

document.querySelector("#busca").oninput = debounce(
  (e) => buscar(e.target.value),
  250,
);
document.querySelector("#busca").onblur = () =>
  setTimeout(() => {
    const caixa = document.querySelector("#resultados");
    if (caixa) caixa.hidden = true;
  }, 150);

document.querySelector("#tema").onclick = () => {
  const html = document.documentElement;
  const escuro = html.dataset.theme
    ? html.dataset.theme === "dark"
    : matchMedia("(prefers-color-scheme: dark)").matches;

  html.dataset.theme = escuro ? "light" : "dark";
  try {
    localStorage.setItem("tema", html.dataset.theme);
  } catch {
    /* sem persistência: o tema vale para esta sessão */
  }
};

window.addEventListener("hashchange", route);

api
  .realm()
  .then((r) => {
    realm = r;
    document.querySelector("#realm").textContent = realmTexto();
  })
  .catch(() => {})
  .finally(route);

// A Blizzard publica um snapshot novo por hora; recarregar mais rápido só
// gastaria requisição para receber o mesmo número de volta.
setInterval(route, 60 * 60 * 1000);

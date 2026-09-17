/**
 * Gráfico de linha em SVG puro, com três séries que podem ser ligadas e
 * desligadas na legenda.
 *
 * Sem biblioteca de gráfico: o desenho são duas funções de escala e um
 * <polyline> por série (ver docs/adr/0002-frontend-sem-build.md).
 *
 * SOBRE O EIXO DUPLO: valor e quantidade vivem em ordens de grandeza
 * diferentes (dezenas de ouro contra centenas de milhares de unidades), então
 * a quantidade usa o eixo da direita. Eixo duplo é um recurso que a literatura
 * de visualização critica com razão — ele deixa ambíguo qual linha se lê em
 * qual escala, e permite sugerir correlação só mudando a escala de um lado.
 * Está aqui porque é o formato pedido para este projeto; a mitigação é
 * amarrar cor a eixo: os dois rótulos do eixo direito saem na cor da série de
 * quantidade. A alternativa sem essa ambiguidade seria dois painéis empilhados
 * compartilhando o eixo do tempo.
 */

const W = 900;
const H = 300;
const PL = 52; // respiro à esquerda para o eixo de ouro
const PR = 62; // à direita, para o eixo de quantidade
const PT = 16;
const PB = 28;

export const SERIES = [
  {
    chave: "value",
    rotulo: "Market Value",
    eixo: "ouro",
    cor: "var(--serie-1)",
  },
  {
    chave: "min_buyout",
    rotulo: "Min Buyout",
    eixo: "ouro",
    cor: "var(--serie-2)",
  },
  { chave: "quantity", rotulo: "Quantity", eixo: "qtd", cor: "var(--serie-3)" },
];

const fmtOuro = (n) =>
  n >= 1e4
    ? (n / 1e3).toFixed(1) + "K"
    : n >= 100
      ? n.toFixed(0)
      : n.toFixed(2);

// Uma casa decimal abaixo de 100K: arredondar 2.435 e 2.087 para "2K" faria os
// cinco rótulos do eixo saírem iguais quando a faixa é estreita.
const fmtQtd = (n) =>
  n >= 1e6
    ? (n / 1e6).toFixed(2) + "M"
    : n >= 1e5
      ? Math.round(n / 1e3) + "K"
      : n >= 1e3
        ? (n / 1e3).toFixed(1) + "K"
        : String(Math.round(n));

/** Mínimo e máximo das séries visíveis de um eixo, com folga de 5%. */
function faixa(pontos, chaves) {
  const vs = [];
  for (const p of pontos) {
    for (const k of chaves) {
      const v = p[k];
      if (typeof v === "number") vs.push(v);
    }
  }
  if (!vs.length) return null;

  const min = Math.min(...vs);
  const max = Math.max(...vs);
  if (min === max) return { min: min * 0.95, max: max * 1.05 || 1 };

  const folga = (max - min) * 0.05;
  return { min: min - folga, max: max + folga };
}

/**
 * @param el     container
 * @param pontos [{ ts, value, min_buyout, quantity }], do mais antigo ao mais novo
 * @param ativas Set com as chaves visíveis
 * @param aoAlternar callback(chave) quando a legenda é clicada
 */
export function desenharGrafico(el, pontos, ativas, aoAlternar) {
  if (!pontos.length) {
    el.innerHTML = '<p class="muted">Sem dados para esta faixa.</p>';
    return;
  }

  const visiveis = SERIES.filter((s) => ativas.has(s.chave));
  const ouro = faixa(
    pontos,
    visiveis.filter((s) => s.eixo === "ouro").map((s) => s.chave),
  );
  const qtd = faixa(
    pontos,
    visiveis.filter((s) => s.eixo === "qtd").map((s) => s.chave),
  );

  const x = (i) => PL + (i * (W - PL - PR)) / (pontos.length - 1 || 1);
  const escala = (f) => (v) =>
    PT + (1 - (v - f.min) / (f.max - f.min)) * (H - PT - PB);
  const yOuro = ouro && escala(ouro);
  const yQtd = qtd && escala(qtd);
  const yDe = (s) => (s.eixo === "ouro" ? yOuro : yQtd);

  // ---- grade e eixos -------------------------------------------------------
  // A grade sai do eixo de ouro quando ele existe; só de quantidade quando é a
  // única série ligada. Duas grades sobrepostas viram ruído.
  const base = ouro || qtd;
  const yBase = ouro ? yOuro : yQtd;
  const linhas = base
    ? [0, 1, 2, 3, 4]
        .map((k) => {
          const v = base.min + ((base.max - base.min) * k) / 4;
          const py = yBase(v).toFixed(1);
          const rot = ouro ? fmtOuro(v) : fmtQtd(v);
          const classe = ouro ? "" : ' class="rotulo-qtd"';
          return `<line x1="${PL}" x2="${W - PR}" y1="${py}" y2="${py}" class="grade"/>
                  <text x="${PL - 8}" y="${+py + 4}" text-anchor="end"${classe}>${rot}</text>`;
        })
        .join("")
    : "";

  // Eixo da direita só aparece quando há série de ouro dividindo a tela com a
  // quantidade. Os rótulos vão na cor da série, que é o que liga um ao outro.
  const eixoDireito =
    ouro && qtd
      ? [0, 1, 2, 3, 4]
          .map((k) => {
            const v = qtd.min + ((qtd.max - qtd.min) * k) / 4;
            return `<text x="${W - PR + 8}" y="${yQtd(v) + 4}" class="rotulo-qtd">${fmtQtd(v)}</text>`;
          })
          .join("")
      : "";

  const datas = [0, 0.5, 1]
    .map((k, n) => {
      const i = Math.round(k * (pontos.length - 1));
      const d = new Date(pontos[i].ts * 1000);
      const texto =
        pontos.length <= 24
          ? d.toLocaleTimeString("pt-BR", {
              hour: "2-digit",
              minute: "2-digit",
            })
          : d.toLocaleDateString("pt-BR");
      return `<text x="${x(i)}" y="${H - 6}" text-anchor="${["start", "middle", "end"][n]}">${texto}</text>`;
    })
    .join("");

  // ---- séries --------------------------------------------------------------
  // Cada linha é desenhada duas vezes: uma grossa na cor do fundo e a colorida
  // em cima. É o que mantém os cruzamentos legíveis sem recorrer a opacidade.
  const traços = visiveis
    .map((s) => {
      const y = yDe(s);
      if (!y) return "";
      const d = pontos
        .map((p, i) =>
          typeof p[s.chave] === "number"
            ? `${x(i).toFixed(1)},${y(p[s.chave]).toFixed(1)}`
            : null,
        )
        .filter(Boolean)
        .join(" ");
      if (!d) return "";
      return `<polyline points="${d}" class="contorno"/>
              <polyline points="${d}" class="serie" style="stroke:${s.cor}"/>`;
    })
    .join("");

  el.innerHTML = `
    <div class="grafico-area">
      <svg viewBox="0 0 ${W} ${H}" role="img"
           aria-label="Histórico de ${visiveis.map((s) => s.rotulo).join(", ") || "nenhuma série"}">
        ${linhas}${eixoDireito}${datas}
        ${traços}
        <line class="cursor" y1="${PT}" y2="${H - PB}" style="display:none"/>
      </svg>
      <div class="dica"></div>
    </div>
    <div class="legenda">
      ${SERIES.map(
        (s) => `
        <button type="button" class="chip ${ativas.has(s.chave) ? "on" : "off"}"
                data-serie="${s.chave}" aria-pressed="${ativas.has(s.chave)}">
          <span class="ponto" style="background:${s.cor}"></span>${s.rotulo}
        </button>`,
      ).join("")}
    </div>`;

  for (const b of el.querySelectorAll(".chip")) {
    b.onclick = () => aoAlternar(b.dataset.serie);
  }

  ligarDica(el, pontos, visiveis, x);
}

function ligarDica(el, pontos, visiveis, x) {
  const svg = el.querySelector("svg");
  const cursor = el.querySelector(".cursor");
  const dica = el.querySelector(".dica");

  const mover = (clientX) => {
    const r = svg.getBoundingClientRect();
    const px = ((clientX - r.left) / r.width) * W;
    const i = Math.max(
      0,
      Math.min(
        pontos.length - 1,
        Math.round(((px - PL) / (W - PL - PR)) * (pontos.length - 1)),
      ),
    );
    const p = pontos[i];
    const cx = x(i);

    cursor.style.display = "";
    cursor.setAttribute("x1", cx);
    cursor.setAttribute("x2", cx);

    const quando = new Date(p.ts * 1000).toLocaleString("pt-BR");
    const itens = visiveis
      .map((s) => {
        const v = p[s.chave];
        if (typeof v !== "number") return "";
        const texto =
          s.eixo === "ouro"
            ? `${fmtOuro(v)} g`
            : Number(v).toLocaleString("pt-BR");
        return `<div><span class="ponto" style="background:${s.cor}"></span>${s.rotulo}: <b>${texto}</b></div>`;
      })
      .join("");

    dica.style.display = "block";
    dica.style.left = `clamp(80px, ${(cx / W) * 100}%, calc(100% - 80px))`;
    dica.innerHTML = `<div class="quando">${quando}</div>${itens || '<div class="muted">nenhuma série ligada</div>'}`;
  };

  svg.addEventListener("mousemove", (e) => mover(e.clientX));
  svg.addEventListener("touchmove", (e) => mover(e.touches[0].clientX), {
    passive: true,
  });
  svg.addEventListener("mouseleave", () => {
    cursor.style.display = "none";
    dica.style.display = "none";
  });
}

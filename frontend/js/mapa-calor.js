// Mapa de calor 7x24 em CSS grid: cada célula é uma div colorida pelo valor
// normalizado. Uma matriz de 168 células não justifica SVG nem canvas.
//
// A cor sai de `color-mix` entre dois tokens da escala do bronze, em vez de um
// `hsl()` calculado no JS: assim a paleta continua morando no CSS, e trocar o
// acento do tema troca o mapa junto.

const DIAS = ["Dom", "Seg", "Ter", "Qua", "Qui", "Sex", "Sáb"];

const fmt = (v) => v.toLocaleString("pt-BR", { maximumFractionDigits: 2 });

export function desenharMapaCalor(el, grid, { rotulo = "" } = {}) {
  const preenchidas = grid.flat().filter((v) => v > 0);

  if (!preenchidas.length) {
    el.innerHTML =
      '<p class="muted">Sem dados suficientes para o padrão semanal.</p>';
    return;
  }

  const min = Math.min(...preenchidas);
  const max = Math.max(...preenchidas);

  const celula = (v) => {
    if (!v) return '<div class="vazio" title="sem dado nesta hora"></div>';
    const k = ((v - min) / (max - min || 1)) * 100;
    return `<div style="background:color-mix(in oklab, var(--sv-glow) ${k.toFixed(1)}%, var(--sv-deep))"
                 title="${fmt(v)}"></div>`;
  };

  const horas = [...Array(24)]
    .map((_, h) => `<div class="rotulo">${h % 3 ? "" : h}</div>`)
    .join("");

  const linhas = grid
    .map(
      (linha, d) =>
        `<div class="rotulo">${DIAS[d]}</div>${linha.map(celula).join("")}`,
    )
    .join("");

  el.innerHTML = `
    <div class="mapa">
      <div></div>${horas}
      ${linhas}
    </div>
    <div class="legenda">
      <span>${fmt(min)}</span>
      <span class="escala" role="presentation"></span>
      <span>${fmt(max)}</span>
      ${rotulo ? `<span class="muted">${rotulo}</span>` : ""}
    </div>`;
}

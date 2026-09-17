// Camada única de acesso ao backend. Todo fetch do app passa por aqui, então
// trocar a base da URL ou acrescentar um header é mudança de um lugar só.
//
// A região não é parâmetro: o app está fixado num realm (Area 52 / US) e o
// backend usa a região dele por padrão. Ver backend/app/config.py.
const BASE = "/api";

async function get(path, params = {}) {
  const url = new URL(BASE + path, location.origin);
  for (const [k, v] of Object.entries(params)) {
    if (v !== "" && v != null) url.searchParams.set(k, v);
  }

  const r = await fetch(url);
  if (!r.ok) throw new Error(`${r.status} em ${path}`);
  return r.json();
}

export const api = {
  realm: () => get("/realm"),
  health: () => get("/health"),
  categories: () => get("/categories"),

  // Filtra as chaves em vez de repassar o state inteiro: o state carrega coisas
  // que só existem na tela (Set de séries, filtro de favoritos) e que virariam
  // query string sem sentido.
  items: ({ q, category, sort, limit } = {}) =>
    get("/items", { q, category, sort, limit }),

  item: (id) => get(`/items/${id}`),
  series: (id, range) => get(`/items/${id}/series`, { range }),
  heatmap: (id, field) => get(`/items/${id}/heatmap`, { field }),
};

// Camada única de acesso ao backend. Todo fetch do app passa por aqui, então
// trocar a base da URL ou acrescentar um header é mudança de um lugar só.
const BASE = '/api';

async function get(path, params = {}) {
  const url = new URL(BASE + path, location.origin);
  for (const [k, v] of Object.entries(params)) if (v !== '' && v != null) url.searchParams.set(k, v);

  const r = await fetch(url);
  if (!r.ok) throw new Error(`${r.status} em ${path}`);
  return r.json();
}

export const api = {
  health: () => get('/health'),
  categories: () => get('/categories'),
  items: (params) => get('/items', params),
  item: (id, region) => get(`/items/${id}`, { region }),
  series: (id, region, range) => get(`/items/${id}/series`, { region, range }),
  heatmap: (id, region, field) => get(`/items/${id}/heatmap`, { region, field }),
};

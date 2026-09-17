/**
 * Teste de ponta a ponta: sobe o servidor, abre as duas telas num Chromium e
 * confere que o que chega da API virou pixel.
 *
 * Existe porque a suíte do pytest para na fronteira do HTTP: ela prova que
 * `/api/items` devolve doze itens, não que a tabela desenhou doze linhas. Os
 * dois bugs que este arquivo pegou primeiro foram exatamente desse tipo — um
 * `import` apontando para o nome antigo do módulo e um parâmetro de callback
 * renomeado só pela metade. Nenhum dos dois aparecia no pytest.
 *
 * Roda com:  node scripts/ponta-a-ponta.mjs
 * O servidor é filho deste processo e morre com ele — nada de porta presa.
 */

import { spawn } from 'node:child_process';
import { mkdirSync } from 'node:fs';
import { chromium } from 'playwright';

const PORTA = process.env.PORTA ?? '8099';
const BASE = `http://localhost:${PORTA}`;
const TELAS = 'telas';

const problemas = [];
const conferir = (condicao, descricao) => {
  if (!condicao) problemas.push(descricao);
  console.log(`${condicao ? 'ok  ' : 'FALHA'} ${descricao}`);
};

const servidor = spawn(
  'python',
  ['-m', 'uvicorn', 'backend.app.main:app', '--port', PORTA, '--log-level', 'warning'],
  { stdio: 'inherit' },
);

const encerrar = (codigo) => {
  servidor.kill();
  process.exit(codigo);
};

async function esperarServidor() {
  for (let i = 0; i < 60; i++) {
    try {
      const r = await fetch(`${BASE}/api/health`);
      if (r.ok) return (await r.json()).snapshots;
    } catch {
      /* ainda subindo */
    }
    await new Promise((r) => setTimeout(r, 300));
  }
  throw new Error('o servidor não respondeu em 18s');
}

try {
  const snapshots = await esperarServidor();
  conferir(snapshots > 0, `o banco tem dados (${snapshots} snapshots)`);

  mkdirSync(TELAS, { recursive: true });
  const navegador = await chromium.launch();
  const pagina = await navegador.newPage({ viewport: { width: 1200, height: 1500 } });

  pagina.on('pageerror', (e) => problemas.push(`erro de JS: ${e.message}`));
  pagina.on('console', (m) => m.type() === 'error' && problemas.push(`console: ${m.text()}`));
  pagina.on('requestfailed', (r) => problemas.push(`requisição falhou: ${r.url()}`));

  // ---- catálogo ----
  await pagina.goto(BASE, { waitUntil: 'networkidle' });
  const linhas = await pagina.locator('tbody tr[data-id]').count();
  conferir(linhas > 0, `o catálogo desenhou linhas (${linhas})`);
  await pagina.screenshot({ path: `${TELAS}/catalogo.png` });

  await pagina.fill('#q', 'ore');
  await pagina.waitForTimeout(600);
  const filtradas = await pagina.locator('tbody tr[data-id]').count();
  conferir(filtradas > 0 && filtradas < linhas, `o filtro reduziu a lista (${filtradas})`);

  // ---- item ----
  await pagina.fill('#q', '');
  await pagina.waitForTimeout(600);
  await pagina.locator('tbody tr[data-id]').first().click();
  await pagina.waitForSelector('#grafico svg');

  conferir((await pagina.locator('.card').count()) >= 5, 'os painéis do item apareceram');

  const pontos = (await pagina.locator('#grafico polyline').getAttribute('points')).trim();
  conferir(pontos.split(/\s+/).length > 10, 'o gráfico tem uma linha com pontos');

  await pagina.waitForSelector('.mapa > div:not(.rotulo)');
  const celulas = await pagina.locator('.mapa > div:not(.rotulo)').count();
  conferir(celulas >= 300, `os dois mapas de calor preencheram (${celulas} células)`);

  // Trocar a faixa tem que redesenhar, não só pintar a aba.
  const antes = pontos;
  await pagina.click('.abas button[data-range="monthly"]');
  await pagina.waitForTimeout(800);
  const depois = (await pagina.locator('#grafico polyline').getAttribute('points')).trim();
  conferir(antes !== depois, 'trocar a faixa redesenhou o gráfico');

  await pagina.screenshot({ path: `${TELAS}/item.png`, fullPage: true });

  // ---- tema ----
  await pagina.click('#tema');
  await pagina.waitForTimeout(400);
  const tema = await pagina.getAttribute('html', 'data-theme');
  conferir(tema === 'dark' || tema === 'light', `o botão de tema aplicou (${tema})`);
  await pagina.screenshot({ path: `${TELAS}/item-escuro.png`, fullPage: true });

  await navegador.close();
} catch (e) {
  problemas.push(e.message);
}

console.log('');
if (problemas.length) {
  console.error(`${problemas.length} problema(s):`);
  for (const p of problemas) console.error(` - ${p}`);
  encerrar(1);
}

console.log('ponta a ponta: tudo certo.');
encerrar(0);

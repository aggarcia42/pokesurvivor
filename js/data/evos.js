/* ============ evos.js — ayudas sobre las cadenas de evolución ============
 * Los datos están en js/data/evolutions.js (generado). Una especie sin entrada
 * se trata como familia de una sola etapa.
 */
G.Evos = (() => {
  const E = dex => G.EVOS[dex] || { fam: dex, evo: [] };

  /** Especie base de la familia. */
  function family(dex) { return E(dex).fam; }

  /** Siguientes etapas: [{ to, lvl }] (varias en las ramas tipo Eevee). */
  function next(dex) { return E(dex).evo; }

  /** Toda la familia en orden de cadena (recorrido en anchura desde la base). */
  function lineOf(dex) {
    const out = [], seen = new Set();
    const queue = [family(dex)];
    while (queue.length) {
      const d = queue.shift();
      if (seen.has(d)) continue;
      seen.add(d); out.push(d);
      for (const x of next(d)) queue.push(x.to);
    }
    return out;
  }

  /** 0 = base, 1 = intermedia, 2 = final (profundidad desde la base). */
  function stage(dex) {
    const fam = family(dex);
    if (fam === dex) return 0;
    const depth = (d, k) => {
      if (d === dex) return k;
      for (const x of next(d)) { const r = depth(x.to, k + 1); if (r >= 0) return r; }
      return -1;
    };
    const k = depth(fam, 0);
    return k < 0 ? 0 : Math.min(2, k);
  }

  /** Bonus de experiencia por empezar pequeño: base +30%, intermedia +15%, final 0. */
  const BONUS = [0.30, 0.15, 0];
  function bonusFor(dex) { return BONUS[stage(dex)]; }

  return { family, next, stage, lineOf, BONUS, bonusFor };
})();

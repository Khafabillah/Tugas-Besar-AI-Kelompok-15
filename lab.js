// lab.js — kerangka eksperimen. Membutuhkan engine.js dimuat lebih dulu.
/* =====================================================================
   LAB — kerangka eksperimen. Murni logika (memakai Engine + Math.random),
   tidak menyentuh DOM. Tidak ada seed tetap: setiap pemanggilan memakai
   Math.random() apa adanya sehingga hasil BERBEDA setiap dijalankan
   (mencerminkan variasi permainan sungguhan, bukan skenario statis).
   ===================================================================== */
const Lab = (function () {

  // ---- lawan simulasi untuk giliran Player ----
  // random : memilih aksi legal secara acak
  // greedy : menyerang terus (power bila siap), minum potion bila HP < 30
  // smart  : mencari 1-ply ke depan dengan alpha-beta depth 2 (bukan agen sempurna)
  function botAction(state, bot) {
    const actions = Engine.getActions(state, 'player');
    if (bot === 'random') return actions[Math.floor(Math.random() * actions.length)];
    if (bot === 'greedy') {
      if (state.player_hp < 30 && actions.includes('potion')) return 'potion';
      return actions.includes('power_attack') ? 'power_attack' : 'attack';
    }
    // smart
    let best = null, bestValue = Infinity;
    for (const a of actions) {
      const next = Engine.applyAction(state, 'player', a);
      const value = Engine.isTerminal(next)
        ? Engine.utility(next)
        : Engine.search(next, 2, { algo: 'alphabeta', ev: 'material' }).value;
      if (value < bestValue) { bestValue = value; best = a; }
    }
    return best;
  }

  /**
   * Mensimulasikan SATU pertandingan penuh NPC (dikendalikan Engine.search
   * dengan konfigurasi `cfg`) melawan bot Player, dari HP 100/100 sampai
   * terminal. stochastic=true membuat serangan bisa meleset sesuai ACCURACY.
   */
  function playMatch(cfg, bot, stochastic) {
    let s = Engine.initState();
    const actionCount = { attack: 0, power_attack: 0, defend: 0, potion: 0, teleport: 0 };
    let totalMs = 0, decisions = 0, totalNodes = 0;

    while (!Engine.isTerminal(s)) {
      if (s.turn === 'player') {
        const a = botAction(s, bot);
        const hit = !stochastic || Math.random() < (Engine.ACCURACY[a] || 1);
        s = Engine.applyAction(s, 'player', a, hit);
      } else {
        const r = Engine.search(s, cfg.depth, cfg);
        totalMs += r.ms; totalNodes += r.nodes; decisions++; actionCount[r.action]++;
        const hit = !stochastic || Math.random() < (Engine.ACCURACY[r.action] || 1);
        s = Engine.applyAction(s, 'npc', r.action, hit);
      }
    }
    const result = s.escaped ? 'escape'
      : (s.player_hp <= 0 && s.npc_hp > 0) ? 'npc_win'
      : (s.npc_hp <= 0 && s.player_hp > 0) ? 'npc_lose'
      : 'draw';
    return { result, plies: s.ply, actionCount, totalMs, decisions, totalNodes, hpMargin: s.npc_hp - s.player_hp };
  }

  /** Menjalankan N pertandingan dan mengagregasi statistiknya. Tanpa seed tetap. */
  function playBatch(cfg, bot, N, stochastic) {
    const agg = {
      npc_win: 0, npc_lose: 0, draw: 0, escape: 0, plies: 0, hpMargin: 0,
      totalMs: 0, decisions: 0, totalNodes: 0,
      actionCount: { attack: 0, power_attack: 0, defend: 0, potion: 0, teleport: 0 }
    };
    for (let i = 0; i < N; i++) {
      const m = playMatch(cfg, bot, stochastic);
      agg[m.result]++;
      agg.plies += m.plies; agg.hpMargin += m.hpMargin;
      agg.totalMs += m.totalMs; agg.decisions += m.decisions; agg.totalNodes += m.totalNodes;
      for (const k in m.actionCount) agg.actionCount[k] += m.actionCount[k];
    }
    return agg;
  }

  /**
   * Menghasilkan `count` state uji dengan MEMAINKAN sejumlah langkah acak
   * dari state awal (bukan state yang ditulis tangan / hardcoded), sehingga
   * kondisi HP/potion/cooldown yang diuji berbeda tiap kali dipanggil.
   *
   * PENTING (diperbaiki): state yang dikembalikan hanya yang `turn === actor`
   * (default 'npc'). Sebelumnya fungsi ini mengembalikan APA PUN giliran
   * terakhir dari permainan acaknya (≈50% ternyata giliran player), padahal
   * E1/E3 memakainya untuk mengukur biaya pencarian NPC pada titik keputusan
   * NPC yang nyata. Karena `Engine.search` menentukan siapa bergerak dari
   * `state.turn`, menguji state bergiliran player berarti mengukur pencarian
   * untuk keputusan player, bukan NPC — tidak representatif untuk E1/E3.
   */
  function sampleStatesFromRandomPlay(count, maxPlies, actor) {
    actor = actor || 'npc';
    const states = [];
    let guard = 0;
    const maxGuard = count * 40; // jaga-jaga agar tidak infinite loop di kasus ekstrem
    while (states.length < count && guard < maxGuard) {
      guard++;
      let s = Engine.initState();
      const plies = 2 + Math.floor(Math.random() * maxPlies);
      for (let p = 0; p < plies && !Engine.isTerminal(s); p++) {
        const who = s.turn;
        const acts = Engine.getActions(s, who);
        const a = acts[Math.floor(Math.random() * acts.length)];
        const hit = Math.random() < (Engine.ACCURACY[a] || 1);
        s = Engine.applyAction(s, who, a, hit);
      }
      if (!Engine.isTerminal(s) && s.turn === actor) states.push(s);
    }
    return states.length ? states : [Engine.initState()];
  }

  const pct = (x, n) => n ? Math.round((100 * x) / n) + '%' : '-';
  const avgMargin = (agg, n) => (agg.hpMargin / n >= 0 ? '+' : '') + (agg.hpMargin / n).toFixed(1);

  // ---------------- E1: Minimax vs Alpha-Beta (node count) ----------------
  function experiment1_minimaxVsAlphaBeta(depths, sampleCount) {
    const states = sampleStatesFromRandomPlay(sampleCount, 16);
    const rows = depths.map(d => {
      let mmNodes = 0, abNodes = 0, mismatches = 0;
      for (const s of states) {
        const mm = Engine.search(s, d, { algo: 'minimax', ev: 'resource' });
        const ab = Engine.search(s, d, { algo: 'alphabeta', ev: 'resource' });
        mmNodes += mm.nodes; abNodes += ab.nodes;
        if (Math.abs(mm.value - ab.value) > 1e-6) mismatches++;
      }
      const n = states.length;
      return [d, Math.round(mmNodes / n), Math.round(abNodes / n),
        (mmNodes / abNodes).toFixed(2) + '×', mismatches === 0 ? 'ya' : (n - mismatches) + '/' + n];
    });
    return {
      title: 'E1 — Minimax vs Alpha-Beta (rata-rata ' + sampleCount + ' state hasil permainan acak)',
      headers: ['Depth', 'Node Minimax', 'Node Alpha-Beta', 'Penghematan', 'Nilai root identik?'],
      rows
    };
  }

  // ---------------- E2: Fungsi evaluasi & perilaku NPC ----------------
  function experiment2_evalFunctions(N) {
    const rows = [];
    for (const ev of Object.keys(Engine.EVALS)) {
      for (const bot of ['random', 'greedy', 'smart']) {
        const agg = playBatch({ algo: 'alphabeta', depth: 4, ev }, bot, N, false);
        const total = Object.values(agg.actionCount).reduce((a, b) => a + b, 0) || 1;
        const q = k => pct(agg.actionCount[k], total);
        rows.push([ev, bot, pct(agg.npc_win, N), pct(agg.npc_lose, N), pct(agg.draw, N), pct(agg.escape, N),
          avgMargin(agg, N), (agg.plies / N).toFixed(1), q('attack'), q('power_attack'), q('defend'), q('potion'), q('teleport')]);
      }
    }
    return {
      title: 'E2 & E5 — Perbandingan fungsi evaluasi dan perilaku NPC (Alpha-Beta, depth 4, N=' + N + ')',
      headers: ['Eval', 'Lawan', 'NPC menang', 'NPC kalah', 'Seri', 'NPC/lawan kabur', 'Δ HP rata²', 'Rata² ply',
        'attack', 'power', 'defend', 'potion', 'teleport'],
      rows
    };
  }

  // ---------------- E3: Urutan aksi ----------------
  function experiment3_actionOrdering(depths, sampleCount) {
    const states = sampleStatesFromRandomPlay(sampleCount, 16);
    const rows = depths.map(d => {
      const acc = { fixed: 0, best: 0, worst: 0 };
      for (const s of states) for (const order of Object.keys(acc)) {
        acc[order] += Engine.search(s, d, { algo: 'alphabeta', ev: 'resource', order }).nodes;
      }
      const n = states.length;
      return [d, Math.round(acc.fixed / n), Math.round(acc.best / n), Math.round(acc.worst / n)];
    });
    return {
      title: 'E3 — Pengaruh urutan aksi terhadap node Alpha-Beta (rata-rata ' + sampleCount + ' state acak)',
      headers: ['Depth', 'Urutan tetap', 'Best-first', 'Worst-first'],
      rows
    };
  }

  // ---------------- E4: Kedalaman ----------------
  function experiment4_depth(depths, N) {
    const rows = depths.map(d => {
      const vsGreedy = playBatch({ algo: 'alphabeta', depth: d, ev: 'resource' }, 'greedy', N, false);
      const vsSmart = playBatch({ algo: 'alphabeta', depth: d, ev: 'resource' }, 'smart', N, false);
      return [d,
        pct(vsGreedy.npc_win, N) + ' (Δ' + avgMargin(vsGreedy, N) + ')',
        pct(vsSmart.npc_win, N) + ' (Δ' + avgMargin(vsSmart, N) + ')',
        Math.round(vsSmart.totalNodes / vsSmart.decisions),
        (vsSmart.totalMs / vsSmart.decisions).toFixed(2)];
    });
    return {
      title: 'E4 — Pengaruh kedalaman pencarian (Alpha-Beta, eval=resource, N=' + N + ')',
      headers: ['Depth', 'Menang vs greedy', 'Menang vs smart', 'Node/keputusan', 'ms/keputusan'],
      rows
    };
  }

  // ---------------- E6: Algoritma & lingkungan probabilistik ----------------
  // budget default (200) sengaja disamakan dengan opsi yang tersedia di
  // dropdown "Early stop" pada game (lihat index.html #earlySel), supaya
  // baris tabel ini bisa direproduksi langsung lewat UI, bukan angka lepas.
  function experiment6_algorithms(N, earlyStopBudget) {
    earlyStopBudget = earlyStopBudget || 200;
    const configs = [
      ['Minimax', { algo: 'minimax' }],
      ['Alpha-Beta', { algo: 'alphabeta' }],
      ['Alpha-Beta + Early Stop (≤' + earlyStopBudget + ' node)', { algo: 'alphabeta', budget: earlyStopBudget }],
      ['Expectimax', { algo: 'expectimax' }]
    ];
    const rows = configs.map(([name, cfg]) => {
      const row = [name];
      for (const stochastic of [false, true]) {
        for (const bot of ['random', 'smart']) {
          const agg = playBatch({ ...cfg, depth: 4, ev: 'resource' }, bot, N, stochastic);
          row.push(pct(agg.npc_win, N) + ' (Δ' + avgMargin(agg, N) + ')');
        }
      }
      return row;
    });
    return {
      title: 'E6 — Algoritma pencarian pada lingkungan deterministik vs probabilistik (depth 4, eval=resource, N=' + N + ')',
      headers: ['Algoritma', 'Deterministik vs random', 'Deterministik vs smart', 'Akurasi acak vs random', 'Akurasi acak vs smart'],
      rows
    };
  }

  return {
    playMatch, playBatch, sampleStatesFromRandomPlay,
    experiment1_minimaxVsAlphaBeta, experiment2_evalFunctions,
    experiment3_actionOrdering, experiment4_depth, experiment6_algorithms
  };
})();

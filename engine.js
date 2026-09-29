// engine.js — logika permainan murni (dipakai bersama oleh lab.js dan ui.js). Tidak ada dependensi lain.
/* =====================================================================
   ENGINE — logika permainan murni (state, aksi, transisi, terminal,
   utility, evaluasi, dan algoritma pencarian). Tidak menyentuh DOM.
   ===================================================================== */
const Engine = (function () {
  const MAX_HP = 100, MAX_PLY = 40;
  const ATTACK_DMG = 18, POWER_DMG = 32, POWER_CD = 2;
  const DEF_REDUCE = 0.6, DEF_HEAL = 4, POTION_HEAL = 30;
  const TELEPORT_HP_THRESHOLD = 35, ESCAPE_UTILITY = -150;
  const ACCURACY = { attack: 0.9, power_attack: 0.7 }; // dipakai Expectimax & mode probabilistik

  function initState() {
    return {
      player_hp: 100, npc_hp: 100,
      player_potions: 2, npc_potions: 2,
      player_defending: false, npc_defending: false,
      player_cd: 0, npc_cd: 0,
      player_teleport: 1, npc_teleport: 1,
      escaped: null, turn: 'player', ply: 0
    };
  }

  const other = actor => (actor === 'player' ? 'npc' : 'player');

  // Branching factor dijaga <= 4: teleport menggantikan slot "defend"
  // saat HP pemilik <= ambang dan masih punya jatah teleport.
  function getActions(state, actor) {
    const actions = ['attack'];
    actions.push(
      state[actor + '_teleport'] > 0 && state[actor + '_hp'] <= TELEPORT_HP_THRESHOLD
        ? 'teleport'
        : 'defend'
    );
    if (state[actor + '_potions'] > 0) actions.push('potion');
    if (state[actor + '_cd'] === 0) actions.push('power_attack');
    return actions;
  }

  function applyAction(state, actor, action, hit = true) {
    const next = { ...state };
    const opponent = other(actor);
    if (next[actor + '_cd'] > 0) next[actor + '_cd']--;

    const applyDefense = dmg => {
      if (next[opponent + '_defending']) {
        dmg *= (1 - DEF_REDUCE);
        next[opponent + '_defending'] = false;
      }
      return dmg;
    };

    switch (action) {
      case 'attack':
        if (hit) next[opponent + '_hp'] = Math.max(0, next[opponent + '_hp'] - applyDefense(ATTACK_DMG));
        break;
      case 'power_attack':
        if (hit) next[opponent + '_hp'] = Math.max(0, next[opponent + '_hp'] - applyDefense(POWER_DMG));
        next[actor + '_cd'] = POWER_CD;
        break;
      case 'defend':
        next[actor + '_defending'] = true;
        next[actor + '_hp'] = Math.min(MAX_HP, next[actor + '_hp'] + DEF_HEAL);
        break;
      case 'potion':
        next[actor + '_potions']--;
        next[actor + '_hp'] = Math.min(MAX_HP, next[actor + '_hp'] + POTION_HEAL);
        break;
      case 'teleport':
        next.escaped = actor;
        next[actor + '_teleport']--;
        break;
    }
    next.turn = opponent;
    next.ply++;
    return next;
  }

  function isTerminal(state) {
    return !!state.escaped || state.player_hp <= 0 || state.npc_hp <= 0 || state.ply >= MAX_PLY;
  }

  // Sudut pandang NPC (MAX)
  function utility(state) {
    if (state.escaped) return ESCAPE_UTILITY;
    if (state.player_hp <= 0 && state.npc_hp > 0) return 1000 + state.npc_hp;
    if (state.npc_hp <= 0 && state.player_hp > 0) return -1000 - state.player_hp;
    if (state.npc_hp <= 0 && state.player_hp <= 0) return 0;
    return state.npc_hp - state.player_hp; // seri karena batas ply
  }

  const EVALS = {
    material: s => s.npc_hp - s.player_hp,
    resource: s => (s.npc_hp - s.player_hp)
      + 6 * (s.npc_potions - s.player_potions)
      + (s.npc_cd === 0 ? 2 : -2) - (s.player_cd === 0 ? 2 : -2),
    aggressive: s => 1.3 * s.npc_hp - 1.8 * s.player_hp,
    defensive: s => 1.8 * s.npc_hp - 1.2 * s.player_hp + 5 * s.npc_potions
  };

  // Urutan aksi sebelum diekspansi: 'fixed' | 'best' | 'worst'
  function orderActions(state, actor, evalFn, order) {
    const actions = getActions(state, actor);
    if (!order || order === 'fixed') return actions;
    const sign = actor === 'npc' ? -1 : 1;
    const score = a => sign * evalFn(applyAction(state, actor, a));
    actions.sort((a, b) => score(a) - score(b));
    return order === 'worst' ? actions.reverse() : actions;
  }

  const BUDGET_EXCEEDED = Symbol('budget_exceeded');

  /**
   * Pencarian adversarial generik.
   * opts: { algo: 'minimax'|'alphabeta'|'expectimax', ev, order, budget, rootActor }
   * budget > 0 mengaktifkan EARLY STOP: iterative deepening yang berhenti
   * begitu jumlah node mencapai budget, memakai hasil kedalaman terakhir
   * yang tuntas.
   *
   * PENTING: root pencarian mengikuti GILIRAN SEBENARNYA dari `state.turn`
   * (atau `opts.rootActor` bila diberikan secara eksplisit), bukan selalu
   * diasumsikan giliran NPC. Ini memperbaiki bug lama: sebelumnya root
   * selalu di-hardcode sebagai giliran NPC (maximizing=true) berapa pun
   * nilai state.turn sebenarnya, sehingga memanggil search() pada state
   * bergiliran player diam-diam menghasilkan pohon yang salah aktor.
   */
  function search(state, maxDepth, opts) {
    const evalFn = EVALS[opts.ev || 'resource'];
    const order = opts.order || 'fixed';
    const useAB = opts.algo === 'alphabeta';
    const useExpectimax = opts.algo === 'expectimax';
    const budget = opts.budget || 0;
    const rootActor = opts.rootActor || state.turn || 'npc';
    const rootMaximizing = rootActor === 'npc'; // NPC = MAX, Player = MIN
    const counters = { nodes: 0, prunes: 0 };
    const t0 = (typeof performance !== 'undefined' ? performance.now() : Date.now());

    function runToDepth(depth) {
      const rootCandidates = [];
      function recurse(s, depthLeft, alpha, beta, maximizing) {
        if (budget && counters.nodes >= budget) throw BUDGET_EXCEEDED;
        counters.nodes++;
        if (isTerminal(s)) return utility(s);
        if (depthLeft === 0) return evalFn(s);

        const actor = maximizing ? 'npc' : 'player';
        const actions = orderActions(s, actor, evalFn, order);
        let best = maximizing ? -Infinity : Infinity;
        let sum = 0;

        for (const action of actions) {
          const pHit = ACCURACY[action] || 1;
          const evalBranch = hit => recurse(applyAction(s, actor, action, hit), depthLeft - 1, alpha, beta, !maximizing);
          const value = (useExpectimax && pHit < 1)
            ? pHit * evalBranch(true) + (1 - pHit) * evalBranch(false)
            : evalBranch(true);

          if (depthLeft === depth) rootCandidates.push([action, value]);

          if (useExpectimax && !maximizing) { sum += value; continue; } // node MIN = rata-rata (lawan diasumsikan acak)

          if (maximizing) {
            if (value > best) best = value;
            if (useAB) alpha = Math.max(alpha, best);
          } else {
            if (value < best) best = value;
            if (useAB) beta = Math.min(beta, best);
          }
          if (useAB && beta <= alpha) { counters.prunes++; break; }
        }
        return (useExpectimax && !maximizing) ? sum / actions.length : best;
      }
      return { value: recurse(state, depth, -Infinity, Infinity, rootMaximizing), candidates: rootCandidates };
    }

    let result = null, reachedDepth = 0;
    for (let d = budget ? 1 : maxDepth; d <= maxDepth; d++) {
      try { result = runToDepth(d); reachedDepth = d; }
      catch (e) { if (e !== BUDGET_EXCEEDED) throw e; break; }
      if (budget && result && Math.abs(result.value) >= 900) break; // sudah menang/kalah pasti
    }
    if (!result) { result = runToDepth(1); reachedDepth = 1; }

    // Root MAX (NPC) memilih nilai tertinggi; root MIN (Player) memilih nilai
    // terendah — arah pengurutan kandidat HARUS mengikuti siapa yang benar2
    // bergiliran di root, bukan selalu "tertinggi = terbaik".
    const candidates = result.candidates.sort((a, b) => rootMaximizing ? b[1] - a[1] : a[1] - b[1]);
    return {
      action: candidates[0][0],
      value: candidates[0][1],
      nodes: counters.nodes,
      prunes: counters.prunes,
      reachedDepth,
      rootActor,
      ms: (typeof performance !== 'undefined' ? performance.now() : Date.now()) - t0,
      candidates
    };
  }

  return {
    MAX_HP, MAX_PLY, ATTACK_DMG, POWER_DMG, POWER_CD, DEF_REDUCE, DEF_HEAL,
    POTION_HEAL, TELEPORT_HP_THRESHOLD, ESCAPE_UTILITY, ACCURACY,
    initState, other, getActions, applyAction, isTerminal, utility,
    EVALS, orderActions, search
  };
})();

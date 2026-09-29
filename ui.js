// ui.js — DOM, canvas, event handler. Membutuhkan engine.js dan lab.js dimuat lebih dulu.
/* =====================================================================
   UI — semua akses DOM, canvas, event handler, dan render tabel.
   Modul ini MEMANGGIL Engine dan Lab, tetapi Engine/Lab tidak pernah
   memanggil balik ke sini. Pemisahan ini membuat logika permainan bisa
   diuji/dipakai ulang tanpa browser.
   ===================================================================== */
const UI = (function () {
  const $ = id => document.getElementById(id);

  // ---------------- Arena heksagon ----------------
  const W = 480, H = 440, HEX_SIZE = 27, RADIUS = 4, CX = W / 2, CY = H / 2, SQ3 = Math.sqrt(3);
  const DIRS = [[1, 0], [1, -1], [0, -1], [-1, 0], [-1, 1], [0, 1]];
  const key = h => h.q + ',' + h.r;
  const inBoard = h => Math.max(Math.abs(h.q), Math.abs(h.r), Math.abs(h.q + h.r)) <= RADIUS;
  const hexDist = (a, b) => {
    const dq = a.q - b.q, dr = a.r - b.r;
    return (Math.abs(dq) + Math.abs(dr) + Math.abs(dq + dr)) / 2;
  };
  const toPixel = h => ({ x: CX + HEX_SIZE * SQ3 * (h.q + h.r / 2), y: CY + HEX_SIZE * 1.5 * h.r });
  function pixelToHex(x, y) {
    const fq = (SQ3 / 3 * (x - CX) - (y - CY) / 3) / HEX_SIZE;
    const fr = (2 / 3 * (y - CY)) / HEX_SIZE;
    const fs = -fq - fr;
    let q = Math.round(fq), r = Math.round(fr), s = Math.round(fs);
    const dq = Math.abs(q - fq), dr = Math.abs(r - fr), ds = Math.abs(s - fs);
    if (dq > dr && dq > ds) q = -r - s; else if (dr > ds) r = -q - s;
    return { q, r };
  }
  const cells = [];
  for (let q = -RADIUS; q <= RADIUS; q++) for (let r = -RADIUS; r <= RADIUS; r++) if (inBoard({ q, r })) cells.push({ q, r });
  const PILLARS = new Set(['0,0', '2,-1', '-2,1', '1,1', '-1,-1', '3,-2', '-3,2']);
  const PLAYER_SAFEZONE = new Set(['-4,4', '-3,4', '-4,3']);
  const NPC_SAFEZONE = new Set(['4,-4', '3,-4', '4,-3']);
  const REGEN_PER_STEP = 10;
  const neighbors = h => DIRS.map(d => ({ q: h.q + d[0], r: h.r + d[1] })).filter(inBoard).filter(n => !PILLARS.has(key(n)));

  // --- garis pandang (line of sight) lewat grid heksagon ---
  // Pilar bukan cuma menghalangi gerakan, tapi juga menghalangi pandangan:
  // jika sebuah pilar berada tepat pada garis lurus antara player dan NPC,
  // battle TIDAK dipicu walau jaraknya <= 2 hex.
  function cubeRoundHex(fq, fr) {
    let fs = -fq - fr;
    let q = Math.round(fq), r = Math.round(fr), s = Math.round(fs);
    const dq = Math.abs(q - fq), dr = Math.abs(r - fr), ds = Math.abs(s - fs);
    if (dq > dr && dq > ds) q = -r - s; else if (dr > ds) r = -q - s;
    return { q, r };
  }
  function hexLine(a, b) {
    const n = hexDist(a, b), pts = [];
    for (let i = 0; i <= n; i++) {
      const t = n === 0 ? 0 : i / n;
      pts.push(cubeRoundHex(a.q + (b.q - a.q) * t, a.r + (b.r - a.r) * t));
    }
    return pts;
  }
  function hasLineOfSight(a, b) {
    const line = hexLine(a, b);
    // abaikan dua ujung garis (posisi player & NPC sendiri)
    return !line.slice(1, -1).some(h => PILLARS.has(key(h)));
  }

  const cv = $('cv'), ctx = cv.getContext('2d'), dpr = Math.min(window.devicePixelRatio || 1, 2);
  cv.width = W * dpr; cv.height = H * dpr;

  const EMOJI = { attack: '⚔️', power_attack: '🔥', defend: '🛡️', potion: '🧪', teleport: '🌀' };

  // ---------------- state permainan (instance ini) ----------------
  let mode, state, playerPos, npcPos, npcAlive, npcBehavior, potionsOnMap, busy, fx = [], shake = 0;

  function resetGame() {
    mode = 'explore'; state = Engine.initState();
    playerPos = { q: -3, r: 3 }; npcPos = { q: 3, r: -3 }; npcAlive = true; npcBehavior = 'chase'; busy = false; fx = [];
    potionsOnMap = new Set(['-3,0', '3,0', '0,3', '0,-3']);
    $('log').innerHTML = ''; $('endBox').innerHTML = '';
    $('candRows').innerHTML = ''; $('statChips').innerHTML = ''; $('hudEmpty').style.display = 'block';
    log('🧭 Klik hex bercahaya di sebelah player untuk bergerak. Ambil 🧪 potion di arena. Zona hijau = safezone-mu.');
    render();
  }
  function log(msg) { const d = document.createElement('div'); d.textContent = msg; $('log').prepend(d); }

  function pickupPotion(who) {
    const pos = who === 'player' ? playerPos : npcPos, k = key(pos);
    if (!potionsOnMap.has(k)) return;
    potionsOnMap.delete(k);
    if (state[who + '_potions'] < 3) state[who + '_potions']++;
    const p = toPixel(pos);
    addFx({ type: 'text', x: p.x, y: p.y - 20, text: '+🧪', color: '#7ee08c', dur: 900 });
    log((who === 'player' ? '🧍 Player' : '🤖 NPC') + ' mengambil potion (sekarang ' + state[who + '_potions'] + ')');
  }
  function applySafezoneRegen(who) {
    const pos = who === 'player' ? playerPos : npcPos;
    const zone = who === 'player' ? PLAYER_SAFEZONE : NPC_SAFEZONE;
    if (!zone.has(key(pos)) || state[who + '_hp'] >= 100) return;
    state[who + '_hp'] = Math.min(100, state[who + '_hp'] + REGEN_PER_STEP);
    const p = toPixel(pos);
    addFx({ type: 'text', x: p.x, y: p.y - 20, text: '+' + REGEN_PER_STEP + ' ❤', color: '#7ee08c', dur: 800 });
  }
  function checkBattleStart() {
    const inRange = npcAlive && !PLAYER_SAFEZONE.has(key(playerPos)) && !NPC_SAFEZONE.has(key(npcPos)) && hexDist(playerPos, npcPos) <= 2;
    if (inRange && !hasLineOfSight(playerPos, npcPos)) {
      log('🧱 NPC dekat tapi terhalang pilar — battle tidak dipicu.');
      return false;
    }
    if (inRange) {
      mode = 'battle'; state.turn = 'player';
      log('⚔️ NPC terlalu dekat! MODE BATTLE dimulai — giliran Player.');
      const m = toPixel({ q: (playerPos.q + npcPos.q) / 2, r: (playerPos.r + npcPos.r) / 2 });
      addFx({ type: 'text', x: m.x, y: m.y - 30, text: 'BATTLE!', color: '#ff4fa3', dur: 1200 });
      shake = 10; render(); return true;
    }
    return false;
  }
  function tryMove(h) {
    if (mode !== 'explore' || busy) return;
    if (hexDist(h, playerPos) !== 1 || !inBoard(h) || PILLARS.has(key(h)) || NPC_SAFEZONE.has(key(h)) || (npcAlive && key(h) === key(npcPos))) return;
    playerPos = h; pickupPotion('player'); applySafezoneRegen('player');
    if (checkBattleStart()) return;
    busy = true; render();
    setTimeout(() => { npcChase(); busy = false; render(); }, 260);
  }
  function npcChase() {
    if (!npcAlive) return;
    if (NPC_SAFEZONE.has(key(npcPos))) state.npc_hp = Math.min(100, state.npc_hp + REGEN_PER_STEP);
    if (npcBehavior === 'recover') {
      if (state.npc_hp < 100) return;
      npcBehavior = 'chase';
      log('🤖 HP NPC sudah penuh. NPC kembali mencari player.');
    }
    const options = neighbors(npcPos).filter(n => key(n) !== key(playerPos) && !PLAYER_SAFEZONE.has(key(n)));
    if (!options.length) return;
    const minDist = Math.min(...options.map(n => hexDist(n, playerPos)));
    const best = options.filter(n => hexDist(n, playerPos) === minDist);
    npcPos = best[Math.floor(Math.random() * best.length)];
    pickupPotion('npc'); checkBattleStart();
  }
  cv.addEventListener('pointerdown', e => {
    const rc = cv.getBoundingClientRect();
    tryMove(pixelToHex((e.clientX - rc.left) * W / rc.width, (e.clientY - rc.top) * H / rc.height));
  });

  // ---------------- efek visual ----------------
  function addFx(o) { o.t = 0; fx.push(o); }
  function playFx(actor, action, dmg, heal) {
    const a = toPixel(actor === 'player' ? playerPos : npcPos), b = toPixel(actor === 'player' ? npcPos : playerPos);
    if (action === 'attack' || action === 'power_attack') {
      const power = action === 'power_attack';
      addFx({ type: 'beam', x1: a.x, y1: a.y, x2: b.x, y2: b.y, color: power ? '#ffb020' : (actor === 'player' ? '#3fd8ff' : '#ff4fa3'), w: power ? 8 : 3, dur: 260 });
      setTimeout(() => {
        if (dmg > 0) { shake = power ? 12 : 6; addFx({ type: 'ring', x: b.x, y: b.y, color: '#ff5d73', dur: 450 }); addFx({ type: 'text', x: b.x, y: b.y - 24, text: '-' + Math.round(dmg), color: '#ff5d73', dur: 900 }); }
        else addFx({ type: 'text', x: b.x, y: b.y - 24, text: 'BLOCK/MISS', color: '#ffd166', dur: 900 });
      }, 220);
    } else if (action === 'defend') {
      addFx({ type: 'ring', x: a.x, y: a.y, color: '#ffd166', dur: 500 });
      addFx({ type: 'text', x: a.x, y: a.y - 24, text: 'GUARD', color: '#ffd166', dur: 900 });
    } else if (action === 'teleport') {
      addFx({ type: 'ring', x: a.x, y: a.y, color: '#7ee08c', dur: 500 });
      addFx({ type: 'text', x: a.x, y: a.y - 24, text: '🌀 TELEPORT', color: '#7ee08c', dur: 900 });
    } else {
      addFx({ type: 'ring', x: a.x, y: a.y, color: '#7ee08c', dur: 500 });
      addFx({ type: 'text', x: a.x, y: a.y - 24, text: '+' + Math.round(heal), color: '#7ee08c', dur: 900 });
    }
  }

  // ---------------- alur battle ----------------
  function shouldHit(action) { return !$('stoch').checked || Math.random() < (Engine.ACCURACY[action] || 1); }

  function playerAct(action) {
    if (mode !== 'battle' || state.turn !== 'player') return;
    const before = state; state = Engine.applyAction(state, 'player', action, shouldHit(action));
    playFx('player', action, before.npc_hp - state.npc_hp, state.player_hp - before.player_hp);
    log(EMOJI[action] + ' Player: ' + action); render();
    if (!checkEnd()) setTimeout(npcTurn, 700);
  }

  function npcTurn() {
    if (mode !== 'battle') return;
    const depth = +$('depthSel').value;
    const opts = { algo: $('algoSel').value, ev: $('evalSel').value, order: $('orderSel').value, budget: +$('earlySel').value };
    const result = Engine.search(state, depth, opts);

    // perbandingan node pada state yang sama, untuk overlay debug
    const compareBudget = opts.budget || 200; // default disamakan dengan Lab.experiment6_algorithms
    const compare = {
      budget: compareBudget,
      minimax: Engine.search(state, depth, { ...opts, algo: 'minimax', budget: 0 }).nodes,
      alphabeta: Engine.search(state, depth, { ...opts, algo: 'alphabeta', budget: 0 }).nodes,
      earlyStop: Engine.search(state, depth, { ...opts, algo: 'alphabeta', budget: compareBudget }),
      expectimax: Engine.search(state, depth, { ...opts, algo: 'expectimax', budget: 0 }).nodes
    };
    renderDebugOverlay(result, opts, depth, compare);

    const before = state; state = Engine.applyAction(state, 'npc', result.action, shouldHit(result.action));
    playFx('npc', result.action, before.player_hp - state.player_hp, state.npc_hp - before.npc_hp);
    log('🤖 NPC: ' + result.action + ' (skor ' + result.value.toFixed(1) + ', nodes ' + result.nodes + ')');
    render(); checkEnd();
  }

  function doEscape(who) {
    const isPlayer = who === 'player';
    state.escaped = null; state.ply = 0; state.turn = 'player'; mode = 'explore';
    if (isPlayer) playerPos = { q: -4, r: 4 };
    else { npcPos = { q: 4, r: -4 }; npcBehavior = 'recover'; }
    const p = toPixel(isPlayer ? playerPos : npcPos);
    addFx({ type: 'ring', x: p.x, y: p.y, color: '#7ee08c', dur: 600 });
    log('🌀 ' + (isPlayer ? 'Player' : 'NPC') + ' teleport ke safezone! Battle berakhir' +
      (isPlayer ? ' — gerak di zona hijau untuk regen +10 HP.' : ' NPC memulihkan HP +10 setiap langkah player sampai penuh, lalu kembali mencari player.'));
    render();
  }

  function checkEnd() {
    if (state.escaped) { const who = state.escaped; setTimeout(() => doEscape(who), 650); return true; }
    if (!Engine.isTerminal(state)) return false;
    let msg;
    if (state.player_hp <= 0 && state.npc_hp > 0) { mode = 'lost'; msg = '💀 NPC menang. Player kalah.'; }
    else if (state.npc_hp <= 0 && state.player_hp > 0) { mode = 'won'; npcAlive = false; msg = '🏆 Player menang!'; }
    else { mode = 'draw'; msg = '🤝 Seri (batas giliran tercapai).'; }
    $('endBox').innerHTML = '<div class="endmsg">' + msg + '</div>'; render(); return true;
  }

  function renderDebugOverlay(result, opts, depth, compare) {
    $('hudEmpty').style.display = 'none';
    const host = $('candRows'); host.innerHTML = '';
    const scores = result.candidates.map(c => c[1]);
    const lo = Math.min(...scores), span = (Math.max(...scores) - lo) || 1;
    result.candidates.forEach(([action, value], i) => {
      const isBest = action === result.action;
      const row = document.createElement('div');
      row.className = 'candRow' + (isBest ? ' best' : '');
      row.style.animationDelay = (i * 70) + 'ms';
      row.innerHTML = '<div class="clabel">' + (isBest ? '👑 ' : '') + EMOJI[action] + ' ' + action + '</div>' +
        '<div class="cbarOuter"><div class="cbarInner"></div></div><div class="cscore">' + value.toFixed(1) + '</div>';
      host.appendChild(row);
      requestAnimationFrame(() => { row.querySelector('.cbarInner').style.width = (5 + 95 * (value - lo) / span) + '%'; });
    });
    const chip = (k, v) => '<div class="chip">' + k + ': <b>' + v + '</b></div>';
    $('statChips').innerHTML =
      chip('Algoritma', opts.algo) + chip('Depth', result.reachedDepth + '/' + depth) + chip('Eval', opts.ev) +
      chip('Urutan aksi', opts.order) + chip('Node', result.nodes) +
      (opts.algo === 'alphabeta' ? chip('Prune', result.prunes) : '') +
      chip('Waktu', result.ms.toFixed(2) + ' ms') +
      '<div class="chip" style="width:100%">Node pada state yang sama → Minimax <b>' + compare.minimax +
      '</b> · Alpha-Beta <b>' + compare.alphabeta + '</b> · Early Stop ≤' + compare.budget + ' <b>' + compare.earlyStop.nodes +
      '</b> (depth ' + compare.earlyStop.reachedDepth + ') · Expectimax <b>' + compare.expectimax + '</b></div>' +
      (opts.algo === 'alphabeta' ? '<div class="chip" style="width:100%">Catatan: skor aksi non-terbaik pada Alpha-Beta adalah batas (bound) akibat pruning, bukan nilai eksak.</div>' : '');
  }

  // ---------------- HUD teks ----------------
  function render() {
    $('pBar').style.width = state.player_hp + '%'; $('nBar').style.width = state.npc_hp + '%';
    $('pVal').textContent = state.player_hp + ' / 100'; $('nVal').textContent = state.npc_hp + ' / 100';
    $('pMeta').textContent = 'Potion: ' + state.player_potions + ' | CD: ' + state.player_cd + ' | Teleport: ' + state.player_teleport;
    $('nMeta').textContent = 'Potion: ' + state.npc_potions + ' | CD: ' + state.npc_cd + ' | Teleport: ' + state.npc_teleport;
    const legal = Engine.getActions(state, 'player'), canAct = mode === 'battle' && state.turn === 'player';
    $('btnAttack').disabled = !canAct;
    $('btnDefend').disabled = !canAct || !legal.includes('defend');
    $('btnTeleport').disabled = !canAct || !legal.includes('teleport');
    $('btnPower').disabled = !canAct || !legal.includes('power_attack');
    $('btnPotion').disabled = !canAct || !legal.includes('potion');
    const tag = $('modeTag');
    if (mode === 'explore') { tag.className = 'tag explore'; tag.textContent = '🧭 EXPLORE'; {
      const near = hexDist(playerPos, npcPos) <= 2;
      const blocked = near && npcAlive && !hasLineOfSight(playerPos, npcPos);
      $('hint').textContent = npcBehavior === 'recover'
        ? 'NPC memulihkan HP di safezone: ' + state.npc_hp + ' / 100'
        : 'Jarak ke NPC: ' + hexDist(playerPos, npcPos) + ' hex (battle di ≤ 2' +
          (blocked ? ', TERHALANG pilar 🧱' : '') + ') · hijau = safezone-mu';
    } }
    else if (mode === 'battle') { tag.className = 'tag battle'; tag.textContent = '⚔️ BATTLE'; $('hint').textContent = state.turn === 'player' ? 'Giliran kamu — pilih aksi' : 'NPC berpikir...'; }
    else { tag.className = 'tag end'; tag.textContent = 'SELESAI'; $('hint').textContent = 'Tekan "Game Baru" untuk main lagi'; }
  }

  // ---------------- render canvas ----------------
  function hexPath(x, y, r) {
    ctx.beginPath();
    for (let i = 0; i < 6; i++) { const a = Math.PI / 180 * (60 * i - 30), px = x + r * Math.cos(a), py = y + r * Math.sin(a); i ? ctx.lineTo(px, py) : ctx.moveTo(px, py); }
    ctx.closePath();
  }
  function drawFighter(pos, color, isNpc, hp, defending, target, now) {
    const p = toPixel(pos); ctx.save(); ctx.translate(p.x, p.y);
    ctx.shadowColor = color; ctx.shadowBlur = 18; ctx.fillStyle = color;
    if (isNpc) {
      const ang = Math.atan2(target.y - p.y, target.x - p.x);
      ctx.beginPath(); for (let i = 0; i < 3; i++) { const a = ang + i * 2 * Math.PI / 3; ctx.lineTo(15 * Math.cos(a), 15 * Math.sin(a)); } ctx.closePath(); ctx.fill();
      ctx.shadowBlur = 0; ctx.fillStyle = '#0b0c14'; ctx.beginPath(); ctx.arc(0, 0, 4, 0, 7); ctx.fill();
    } else {
      ctx.beginPath(); ctx.arc(0, 0, 11, 0, 7); ctx.fill(); ctx.shadowBlur = 0;
      ctx.fillStyle = '#0b0c14'; ctx.beginPath(); ctx.arc(0, 0, 5, 0, 7); ctx.fill();
      ctx.strokeStyle = color; ctx.lineWidth = 2; ctx.setLineDash([6, 6]); ctx.lineDashOffset = -now / 40;
      ctx.beginPath(); ctx.arc(0, 0, 18, 0, 7); ctx.stroke(); ctx.setLineDash([]);
    }
    if (defending) { ctx.strokeStyle = '#ffd166'; ctx.lineWidth = 3; ctx.beginPath(); ctx.arc(0, 0, 23, 0, 7); ctx.stroke(); }
    ctx.shadowBlur = 0; ctx.fillStyle = '#222436'; ctx.fillRect(-20, -32, 40, 5);
    ctx.fillStyle = color; ctx.fillRect(-20, -32, 40 * Math.max(0, hp) / 100, 5);
    ctx.restore();
  }
  let last = performance.now();
  function frame(now) {
    const dt = now - last; last = now;
    ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    ctx.fillStyle = '#0b0c14'; ctx.fillRect(0, 0, W, H);
    shake *= 0.88; ctx.save(); ctx.translate((Math.random() - 0.5) * shake, (Math.random() - 0.5) * shake);
    const reach = (mode === 'explore' && !busy) ? new Set(neighbors(playerPos).filter(n => !(npcAlive && key(n) === key(npcPos))).map(key)) : new Set();
    if (mode === 'explore' && npcAlive && hexDist(playerPos, npcPos) <= 2 && !hasLineOfSight(playerPos, npcPos)) {
      const a = toPixel(playerPos), b = toPixel(npcPos);
      ctx.strokeStyle = 'rgba(255,93,115,.5)'; ctx.lineWidth = 1.5; ctx.setLineDash([4, 4]);
      ctx.beginPath(); ctx.moveTo(a.x, a.y); ctx.lineTo(b.x, b.y); ctx.stroke(); ctx.setLineDash([]);
    }
    for (const h of cells) {
      const p = toPixel(h), k = key(h);
      hexPath(p.x, p.y, HEX_SIZE - 2);
      ctx.fillStyle = '#141628'; ctx.fill(); ctx.strokeStyle = '#272b4a'; ctx.lineWidth = 1; ctx.stroke();
      if (PLAYER_SAFEZONE.has(k)) { ctx.fillStyle = 'rgba(126,224,140,.16)'; ctx.fill(); ctx.strokeStyle = 'rgba(126,224,140,.55)'; ctx.stroke(); }
      if (NPC_SAFEZONE.has(k)) { ctx.fillStyle = 'rgba(255,209,102,.12)'; ctx.fill(); ctx.strokeStyle = 'rgba(255,209,102,.45)'; ctx.stroke(); }
      if (mode === 'explore' && npcAlive) {
        const d = hexDist(h, npcPos);
        if (d <= 2) { ctx.fillStyle = 'rgba(255,79,163,.07)'; ctx.fill(); }
        if (d === 2) { ctx.strokeStyle = 'rgba(255,79,163,.4)'; ctx.stroke(); }
      }
      if (PILLARS.has(k) && mode === 'explore' && npcAlive && hexDist(playerPos, npcPos) <= 2 && !hasLineOfSight(playerPos, npcPos) && hexLine(playerPos, npcPos).slice(1, -1).some(x => key(x) === k)) {
        ctx.strokeStyle = '#ff5d73'; ctx.lineWidth = 2.5; hexPath(p.x, p.y, HEX_SIZE - 5); ctx.stroke(); // pilar yang sedang menghalangi ditandai merah
      }
      if (reach.has(k)) {
        ctx.fillStyle = 'rgba(63,216,255,.12)'; ctx.fill();
        ctx.strokeStyle = 'rgba(63,216,255,' + (0.5 + 0.35 * Math.sin(now / 220)) + ')'; ctx.lineWidth = 2; ctx.stroke();
      }
      if (PILLARS.has(k)) {
        hexPath(p.x, p.y, HEX_SIZE - 8); ctx.fillStyle = '#2b2f55'; ctx.fill(); ctx.strokeStyle = '#5b62a8'; ctx.lineWidth = 1.5; ctx.stroke();
        ctx.beginPath(); ctx.moveTo(p.x, p.y - 10); ctx.lineTo(p.x + 6, p.y); ctx.lineTo(p.x, p.y + 10); ctx.lineTo(p.x - 6, p.y); ctx.closePath();
        ctx.fillStyle = '#7d86e0'; ctx.fill();
      }
      if (potionsOnMap.has(k)) {
        const b = Math.sin(now / 300) * 2;
        ctx.save(); ctx.shadowColor = '#7ee08c'; ctx.shadowBlur = 12; ctx.fillStyle = '#7ee08c';
        ctx.beginPath(); ctx.arc(p.x, p.y + 3 + b, 7, 0, 7); ctx.fill(); ctx.fillRect(p.x - 2.5, p.y - 8 + b, 5, 6); ctx.restore();
      }
    }
    if (mode === 'battle' || mode === 'won' || mode === 'lost' || mode === 'draw') {
      if (mode === 'battle') { ctx.fillStyle = 'rgba(5,5,12,.5)'; ctx.fillRect(-20, -20, W + 40, H + 40); }
      const a = toPixel(playerPos), b = toPixel(npcPos);
      if (mode === 'battle') {
        ctx.strokeStyle = 'rgba(255,255,255,.35)'; ctx.lineWidth = 1.5; ctx.setLineDash([5, 6]); ctx.lineDashOffset = -now / 50;
        ctx.beginPath(); ctx.moveTo(a.x, a.y); ctx.lineTo(b.x, b.y); ctx.stroke(); ctx.setLineDash([]);
        ctx.fillStyle = '#fff'; ctx.font = 'bold 13px system-ui'; ctx.textAlign = 'center'; ctx.fillText('VS', (a.x + b.x) / 2, (a.y + b.y) / 2 - 8);
      }
    }
    const pp = toPixel(playerPos), np = toPixel(npcPos);
    drawFighter(playerPos, '#3fd8ff', false, state.player_hp, state.player_defending, np, now);
    if (npcAlive) drawFighter(npcPos, '#ff4fa3', true, state.npc_hp, state.npc_defending, pp, now);
    for (let i = fx.length - 1; i >= 0; i--) {
      const o = fx[i]; o.t += dt; const p = Math.min(1, o.t / o.dur);
      ctx.save();
      if (o.type === 'beam') {
        ctx.strokeStyle = o.color; ctx.lineWidth = o.w; ctx.shadowColor = o.color; ctx.shadowBlur = 14; ctx.lineCap = 'round';
        const hx = o.x1 + (o.x2 - o.x1) * p, hy = o.y1 + (o.y2 - o.y1) * p, tp = Math.max(0, p - 0.35), tx = o.x1 + (o.x2 - o.x1) * tp, ty = o.y1 + (o.y2 - o.y1) * tp;
        ctx.beginPath(); ctx.moveTo(tx, ty); ctx.lineTo(hx, hy); ctx.stroke();
      } else if (o.type === 'ring') {
        ctx.globalAlpha = 1 - p; ctx.strokeStyle = o.color; ctx.lineWidth = 3; ctx.beginPath(); ctx.arc(o.x, o.y, 10 + 32 * p, 0, 7); ctx.stroke();
      } else {
        ctx.globalAlpha = 1 - p * p; ctx.fillStyle = o.color; ctx.font = 'bold 16px system-ui'; ctx.textAlign = 'center'; ctx.fillText(o.text, o.x, o.y - 30 * p);
      }
      ctx.restore();
      if (o.t >= o.dur) fx.splice(i, 1);
    }
    ctx.restore();
    requestAnimationFrame(frame);
  }

  // ---------------- panel Lab Eksperimen ----------------
  function tableToHtml(t) {
    let html = '<h4>' + t.title + '</h4><table><tr>' + t.headers.map(h => '<th>' + h + '</th>').join('') + '</tr>';
    for (const row of t.rows) html += '<tr>' + row.map(c => '<td>' + c + '</td>').join('') + '</tr>';
    return html + '</table>';
  }
  function tableToMarkdown(t) {
    const md = ['### ' + t.title, '| ' + t.headers.join(' | ') + ' |', '|' + t.headers.map(() => '---').join('|') + '|'];
    for (const row of t.rows) md.push('| ' + row.join(' | ') + ' |');
    return md.join('\n');
  }
  let lastMarkdown = '';
  function runExperiment(name) {
    const N = Math.max(4, +$('labN').value || 12);
    const out = $('labOut'); const btn = $('run_' + name);
    if (btn) btn.disabled = true;
    setTimeout(() => {
      let table;
      switch (name) {
        case 'e1': table = Lab.experiment1_minimaxVsAlphaBeta([2, 4, 6, 8], N); break;
        case 'e2': table = Lab.experiment2_evalFunctions(N); break;
        case 'e3': table = Lab.experiment3_actionOrdering([2, 4, 6, 8], N); break;
        case 'e4': table = Lab.experiment4_depth([1, 2, 3, 4, 5, 6], N); break;
        case 'e6': table = Lab.experiment6_algorithms(N); break;
      }
      const box = document.createElement('div'); box.className = 'labResult'; box.innerHTML = tableToHtml(table);
      out.prepend(box);
      lastMarkdown = tableToMarkdown(table) + '\n\n' + lastMarkdown;
      $('copyLab').disabled = false;
      if (btn) btn.disabled = false;
    }, 30);
  }
  function bindLabButtons() {
    ['e1', 'e2', 'e3', 'e4', 'e6'].forEach(name => { const b = $('run_' + name); if (b) b.onclick = () => runExperiment(name); });
    $('copyLab').onclick = () => { if (navigator.clipboard) navigator.clipboard.writeText(lastMarkdown); };
    $('clearLab').onclick = () => { $('labOut').innerHTML = ''; lastMarkdown = ''; $('copyLab').disabled = true; };
  }

  function bindGameControls() {
    $('btnAttack').onclick = () => playerAct('attack');
    $('btnPower').onclick = () => playerAct('power_attack');
    $('btnDefend').onclick = () => playerAct('defend');
    $('btnPotion').onclick = () => playerAct('potion');
    $('btnTeleport').onclick = () => playerAct('teleport');
    $('reset').onclick = resetGame;
  }

  function init() {
    bindGameControls();
    bindLabButtons();
    resetGame();
    requestAnimationFrame(frame);
  }

  return { init };
})();

document.addEventListener('DOMContentLoaded', UI.init);

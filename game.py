"""
Tubes 1 — Pergerakan NPC dengan UCS & A* (versi Streamlit)
============================================================
Satu fungsi search() dipakai untuk UCS & A* — cuma beda rumus
priority-nya (g saja, atau g+h). Baca komentar di search()
kalau perlu jelasin logikanya ke dosen.

Tekan "Play pencarian" untuk lihat urutan node yang di-expand
(kotak ungu) sebelum jalur akhirnya (kotak kuning) muncul.

Jalankan:
    pip install -r requirements.txt
    streamlit run app.py
"""

import heapq
import math
import random
import time
from dataclasses import dataclass, field

import pandas as pd
import streamlit as st
from PIL import Image, ImageDraw, ImageFont
from streamlit_image_coordinates import streamlit_image_coordinates

# ----------------------------------------------------------------------
# CONSTANTS
# ----------------------------------------------------------------------
COLS, ROWS, CELL = 22, 14, 28
EMPTY, TREE, HOUSE, RIVER, WALL = 0, 1, 2, 3, 4
TERRAIN_COST = {EMPTY: 1, RIVER: 4}  # TREE / HOUSE / WALL = blocked
TERRAIN_COLOR = {
    EMPTY: (251, 250, 247),
    TREE: (47, 107, 58),
    HOUSE: (138, 109, 85),
    RIVER: (143, 208, 236),
    WALL: (90, 92, 99),
}
TERRAIN_EMOJI = {
    EMPTY: "",
    TREE: "🌲",
    HOUSE: "🏠",
    RIVER: "🌊",
    WALL: "🧱",
}
EXPANDED_COLOR = (205, 184, 240)
PATH_COLOR = (255, 214, 10)  # kuning terang — sengaja beda jauh dari semua warna terrain
NPC_COLOR = (224, 134, 43)
PLAYER_COLOR = (43, 95, 217)
SQRT2 = math.sqrt(2)

st.set_page_config(page_title="Tubes 1 — NPC Pathfinding", layout="wide")

# ----------------------------------------------------------------------
# SEARCH ALGORITHMS (UCS / Greedy / A* — satu fungsi, beda priority)
# ----------------------------------------------------------------------
@dataclass(order=True)
class HeapItem:
    priority: float
    tiebreak: int = field(compare=True)
    node: tuple = field(compare=False)
    g: float = field(compare=False)


def heuristic(name, a, b):
    dx, dy = abs(a[0] - b[0]), abs(a[1] - b[1])
    if name == "manhattan":
        return dx + dy
    if name == "euclidean":
        return math.hypot(dx, dy)
    return 0


def in_bounds(x, y):
    return 0 <= x < COLS and 0 <= y < ROWS


def is_blocked(grid, x, y):
    return grid[y][x] in (TREE, HOUSE, WALL)


def neighbors(grid, node, diagonal):
    x, y = node
    dirs = [(1, 0), (-1, 0), (0, 1), (0, -1)]
    if diagonal:
        dirs += [(1, 1), (1, -1), (-1, 1), (-1, -1)]
    out = []
    for dx, dy in dirs:
        nx, ny = x + dx, y + dy
        if not in_bounds(nx, ny) or is_blocked(grid, nx, ny):
            continue
        if dx != 0 and dy != 0:  # jangan motong lewat sudut dinding
            if is_blocked(grid, x + dx, y) and is_blocked(grid, x, y + dy):
                continue
        move_cost = SQRT2 if (dx != 0 and dy != 0) else 1
        out.append((nx, ny, move_cost))
    return out


def search(grid, algo, start, goal, heuristic_name, diagonal):
    """
    algo == 'ucs'    -> priority = g          (h dipaksa 0)
    algo == 'astar'  -> priority = g + h
    """
    t0 = time.perf_counter()
    counter = 0  # tie-breaker biar heapq stabil (tuple nggak sortable)

    g_score = {start: 0}
    came_from = {}
    closed = set()
    expanded_order = []

    h0 = 0 if algo == "ucs" else heuristic(heuristic_name, start, goal)
    heap = [HeapItem(priority=h0, tiebreak=counter, node=start, g=0)]

    while heap:
        current = heapq.heappop(heap)
        if current.node in closed:
            continue  # entry basi (node sudah pernah di-expand dgn g lebih baik)
        closed.add(current.node)
        expanded_order.append(current.node)

        if current.node == goal:
            path = [current.node]
            n = current.node
            while n in came_from:
                n = came_from[n]
                path.append(n)
            path.reverse()
            return {
                "found": True,
                "path": path,
                "cost": g_score[current.node],
                "expanded_order": expanded_order,
                "expanded_count": len(expanded_order),
                "time_ms": (time.perf_counter() - t0) * 1000,
            }

        for nx, ny, move_cost in neighbors(grid, current.node, diagonal):
            nb = (nx, ny)
            if nb in closed:
                continue
            terrain = TERRAIN_COST.get(grid[ny][nx], 1)
            tentative_g = g_score[current.node] + move_cost * terrain
            if tentative_g < g_score.get(nb, math.inf):
                g_score[nb] = tentative_g
                came_from[nb] = current.node
                h = 0 if algo == "ucs" else heuristic(heuristic_name, nb, goal)
                priority = tentative_g + h  # UCS: h=0 -> priority=g. A*: priority=g+h
                counter += 1
                heapq.heappush(heap, HeapItem(priority=priority, tiebreak=counter, node=nb, g=tentative_g))

    return {
        "found": False,
        "path": [],
        "cost": math.inf,
        "expanded_order": expanded_order,
        "expanded_count": len(expanded_order),
        "time_ms": (time.perf_counter() - t0) * 1000,
    }


# ----------------------------------------------------------------------
# SESSION STATE
# ----------------------------------------------------------------------
def new_grid():
    return [[EMPTY for _ in range(COLS)] for _ in range(ROWS)]


if "grid" not in st.session_state:
    st.session_state.grid = new_grid()
    st.session_state.npc = (1, 1)
    st.session_state.player = (COLS - 2, ROWS - 2)
    st.session_state.last_click = None
    st.session_state.result = None
    st.session_state.show_overlay = False  # jalur/expanded baru kelihatan setelah Play
    st.session_state.play_now = False
    st.session_state.walk_now = False  # animasi NPC berjalan sampai ke Player


def recompute():
    algo = st.session_state.get("algo", "astar")
    heur = st.session_state.get("heur", "manhattan")
    diagonal = st.session_state.get("diagonal", False)
    st.session_state.result = search(
        st.session_state.grid, algo, st.session_state.npc, st.session_state.player, heur, diagonal
    )
    # apa pun yang berubah (map/posisi/algoritma) -> sembunyikan overlay lama,
    # tunggu user pencet Play lagi buat lihat proses pencarian yang baru.
    st.session_state.show_overlay = False


def move_player(dx, dy):
    x, y = st.session_state.player
    nx, ny = x + dx, y + dy
    if in_bounds(nx, ny) and not is_blocked(st.session_state.grid, nx, ny):
        st.session_state.player = (nx, ny)
        recompute()
        if st.session_state.get("auto_chase", True):
            step_npc()


def step_npc():
    r = st.session_state.result
    if r and r["found"] and len(r["path"]) > 1:
        st.session_state.npc = r["path"][1]
        recompute()


def random_map():
    grid = new_grid()
    for _ in range(70):
        x, y = random.randrange(COLS), random.randrange(ROWS)
        grid[y][x] = random.choice([TREE, HOUSE, RIVER])
    st.session_state.grid = grid
    st.session_state.npc = (1, 1)
    st.session_state.player = (COLS - 2, ROWS - 2)
    grid[st.session_state.npc[1]][st.session_state.npc[0]] = EMPTY
    grid[st.session_state.player[1]][st.session_state.player[0]] = EMPTY
    recompute()


def clear_map():
    st.session_state.grid = new_grid()
    recompute()


def corridor_preset():
    """Replikasi slide 17: jalur lurus tapi mahal (river) vs jalan memutar."""
    grid = new_grid()
    st.session_state.npc = (1, 6)
    st.session_state.player = (COLS - 2, 6)
    for y in range(2, 11):
        for x in range(8, 12):
            grid[y][x] = RIVER if y == 6 else TREE
    st.session_state.grid = grid
    recompute()


if st.session_state.result is None:
    recompute()

# ----------------------------------------------------------------------
# IMAGE RENDERING
# ----------------------------------------------------------------------
def blend(base, overlay, alpha):
    return tuple(int(base[i] * (1 - alpha) + overlay[i] * alpha) for i in range(3))


def render_image(expanded_subset=None, show_path=False):
    """
    expanded_subset: list node yang mau digambar ungu (dipakai buat frame animasi
                      Play — kalau None dan show_path False, peta polos tanpa overlay).
    show_path: True -> gambar jalur akhir (kuning) dari st.session_state.result.
    """
    W, H = COLS * CELL, ROWS * CELL
    img = Image.new("RGB", (W, H), (251, 250, 247))
    draw = ImageDraw.Draw(img)
    grid = st.session_state.grid

    for y in range(ROWS):
        for x in range(COLS):
            color = TERRAIN_COLOR[grid[y][x]]
            draw.rectangle([x * CELL, y * CELL, (x + 1) * CELL - 1, (y + 1) * CELL - 1], fill=color)

    result = st.session_state.result
    if expanded_subset:
        for (x, y) in expanded_subset:
            base = TERRAIN_COLOR[grid[y][x]]
            draw.rectangle(
                [x * CELL, y * CELL, (x + 1) * CELL - 1, (y + 1) * CELL - 1],
                fill=blend(base, EXPANDED_COLOR, 0.6),
            )
    if show_path and result and result["found"]:
        for (x, y) in result["path"]:
            base = TERRAIN_COLOR[grid[y][x]]
            draw.rectangle(
                [x * CELL, y * CELL, (x + 1) * CELL - 1, (y + 1) * CELL - 1],
                fill=blend(base, PATH_COLOR, 0.75),
            )

    try:
        terrain_font = ImageFont.truetype("seguiemj.ttf", 20)
    except OSError:
        terrain_font = ImageFont.load_default()
    for y in range(ROWS):
        for x in range(COLS):
            emoji = TERRAIN_EMOJI[grid[y][x]]
            box = draw.textbbox((0, 0), emoji, font=terrain_font)
            text_w, text_h = box[2] - box[0], box[3] - box[1]
            text_x = x * CELL + (CELL - text_w) // 2 - box[0]
            text_y = y * CELL + (CELL - text_h) // 2 - box[1]
            draw.text((text_x, text_y), emoji, font=terrain_font, fill=(30, 30, 30))

    # gridlines
    for x in range(COLS + 1):
        draw.line([(x * CELL, 0), (x * CELL, H)], fill=(0, 0, 0, 30))
    for y in range(ROWS + 1):
        draw.line([(0, y * CELL), (W, y * CELL)], fill=(0, 0, 0, 30))

    # tokens
    def token(pos, color, label):
        cx, cy = pos[0] * CELL + CELL // 2, pos[1] * CELL + CELL // 2
        r = CELL * 0.4
        draw.ellipse([cx - r, cy - r, cx + r, cy + r], fill=color)
        draw.text((cx - 4, cy - 7), label, fill=(255, 255, 255))

    token(st.session_state.npc, NPC_COLOR, "N")
    token(st.session_state.player, PLAYER_COLOR, "P")
    return img


# ----------------------------------------------------------------------
# UI
# ----------------------------------------------------------------------
st.title("🧭 Tubes 1 — Pergerakan NPC dengan UCS & A*")
st.caption("NPC (N, oranye) mengejar Player (P, biru). Klik peta untuk edit terrain / posisi.")

col_map, col_ctrl = st.columns([2, 1], gap="large")

with col_ctrl:
    st.subheader("Algoritma")
    st.selectbox("Algoritma", ["ucs", "astar"], index=1, key="algo",
                 format_func=lambda a: {"ucs": "Uniform-Cost Search (h=0)",
                                         "astar": "A* (f=g+h)"}[a],
                 on_change=recompute)
    st.selectbox("Heuristik h(n)", ["manhattan", "euclidean"],
                 key="heur", disabled=(st.session_state.get("algo") == "ucs"), on_change=recompute)
    st.checkbox("Gerak diagonal (8 arah)", key="diagonal", on_change=recompute)

    diagonal = st.session_state.get("diagonal", False)
    heur = st.session_state.get("heur", "manhattan")
    if heur == "manhattan" and diagonal:
        st.warning(
            "⚠ Manhattan bisa overestimate saat gerak diagonal aktif "
            "(mis. dx=1,dy=1 → h=2, padahal biaya diagonal asli √2≈1.41) "
            "→ tidak admissible → A* bisa suboptimal. Pakai Euclidean kalau diagonal aktif."
        )
    else:
        st.success("✅ Kombinasi heuristik & mode gerak ini admissible (h(n) tidak pernah overestimate).")

    st.subheader("▶ Jalankan pencarian")
    st.slider("Kecepatan animasi (ms per node)", 10, 300, 60, key="anim_speed")
    if st.button("▶ Play pencarian (animasikan expand node)", use_container_width=True):
        st.session_state.play_now = True
    st.caption(
        "Kotak **ungu** = tiap node yang di-*expand* algoritma (termasuk jalan buntu). "
        "Kotak **kuning** di akhir = jalur solusi final hasil `reconstructPath()`."
    )

    st.subheader("Statistik pencarian terakhir")
    r = st.session_state.result
    c1, c2 = st.columns(2)
    c1.metric("Nodes Expanded", r["expanded_count"] if r else "–")
    c2.metric("Path Cost", f'{r["cost"]:.2f}' if r and r["found"] else "–")
    c3, c4 = st.columns(2)
    c3.metric("Path Length", len(r["path"]) if r and r["found"] else "–")
    c4.metric("Waktu", f'{r["time_ms"]:.2f} ms' if r else "–")
    if r and not r["found"]:
        st.error("Tidak ada jalur ke Player (terhalang total).")

    st.subheader("Gerakkan Player")
    b1, b2, b3 = st.columns(3)
    with b2:
        st.button("⬆", on_click=move_player, args=(0, -1), use_container_width=True)
    b4, b5, b6 = st.columns(3)
    with b4:
        st.button("⬅", on_click=move_player, args=(-1, 0), use_container_width=True)
    with b5:
        st.button("⬇", on_click=move_player, args=(0, 1), use_container_width=True)
    with b6:
        st.button("➡", on_click=move_player, args=(1, 0), use_container_width=True)
    st.checkbox("Auto-chase (NPC otomatis melangkah)", value=True, key="auto_chase")
    st.button("▶ Langkahkan NPC 1x manual", on_click=step_npc)

    st.subheader("🏃 Animasi NPC berjalan ke tujuan")
    st.slider("Kecepatan jalan (ms per langkah)", 50, 800, 200, key="walk_speed")
    if st.button("🏃 Animasikan NPC sampai ke Player", use_container_width=True):
        st.session_state.walk_now = True
    st.caption(
        "NPC akan melangkah beneran cell-per-cell mengikuti jalur hasil pencarian "
        "sampai posisinya sama dengan Player — bukan cuma lompat langsung ke tujuan."
    )

    st.subheader("Bandingkan algoritma")
    if st.button("📊 Jalankan UCS vs A*"):
        rows = []
        results = {
            a: search(st.session_state.grid, a, st.session_state.npc, st.session_state.player, heur, diagonal)
            for a in ["ucs", "astar"]
        }
        best_cost = min(res["cost"] for res in results.values() if res["found"])
        for a, res in results.items():
            optimal = res["found"] and abs(res["cost"] - best_cost) < 1e-6
            rows.append({
                "Algoritma": a.upper(),
                "Nodes Expanded": res["expanded_count"],
                "Path Cost": round(res["cost"], 2) if res["found"] else "—",
                "Optimal?": "✅" if optimal else ("❌ suboptimal" if res["found"] else "—"),
            })
        st.dataframe(pd.DataFrame(rows), hide_index=True, use_container_width=True)

with col_map:
    st.subheader("Peta")
    tool = st.radio(
        "Alat edit (klik peta di bawah setelah pilih alat)",
        ["empty", "tree", "house", "river", "wall", "npc", "player"],
        format_func=lambda t: {"empty": "🧹 Empty", "tree": "🌲 Tree", "house": "🏠 House",
                                "river": "🌊 River (cost 4)", "wall": "🧱 Wall/Tembok (blocked)",
                                "npc": "🤖 Set NPC (start)",
                                "player": "🧑 Set Player (goal)"}[t],
        horizontal=True,
        key="tool",
    )

    if st.session_state.get("play_now"):
        # --- ANIMASI: reveal expanded nodes satu-satu, baru jalur kuning di akhir ---
        placeholder = st.empty()
        result = st.session_state.result
        order = result["expanded_order"] if result else []
        delay = st.session_state.get("anim_speed", 60) / 1000.0

        progress = st.progress(0)
        for i in range(1, len(order) + 1):
            placeholder.image(render_image(expanded_subset=order[:i], show_path=False))
            progress.progress(i / len(order))
            time.sleep(delay)
        placeholder.image(render_image(expanded_subset=order, show_path=True))
        progress.empty()

        if not (result and result["found"]):
            st.error("Tidak ada jalur ke Player (terhalang total) — semua node sudah di-expand.")

        st.session_state.show_overlay = True
        st.session_state.play_now = False
        st.button("Selesai — kembali edit peta", use_container_width=True)  # cukup buat trigger rerun berikutnya

    elif st.session_state.get("walk_now"):
        # --- ANIMASI: NPC melangkah cell-per-cell sepanjang path sampai ke Player ---
        placeholder = st.empty()
        result = st.session_state.result
        path = result["path"] if (result and result["found"]) else []
        delay = st.session_state.get("walk_speed", 200) / 1000.0
        show = st.session_state.get("show_overlay", False)
        expanded_bg = result["expanded_order"] if (show and result) else None

        if len(path) < 2:
            st.info("NPC sudah di posisi Player (atau tidak ada jalur yang bisa dilalui).")
            placeholder.image(render_image(expanded_subset=expanded_bg, show_path=True))
        else:
            progress = st.progress(0)
            total_steps = len(path) - 1
            for i, node in enumerate(path[1:], start=1):
                st.session_state.npc = node  # geser NPC satu cell
                placeholder.image(render_image(expanded_subset=expanded_bg, show_path=True))
                progress.progress(i / total_steps)
                time.sleep(delay)
            progress.empty()
            st.success("🎉 NPC sudah sampai di posisi Player!")
            recompute()  # posisi NPC berubah -> hitung ulang statistik (path cost ~0 sekarang)

        st.session_state.walk_now = False
        st.button("Selesai jalan — kembali edit peta", use_container_width=True)

    else:
        # --- MODE NORMAL: peta polos (atau overlay hasil Play terakhir), bisa diklik utk edit ---
        show = st.session_state.get("show_overlay", False)
        result = st.session_state.result
        img = render_image(
            expanded_subset=(result["expanded_order"] if (show and result) else None),
            show_path=show,
        )
        coords = streamlit_image_coordinates(img, key="map_click")

        if coords is not None and coords != st.session_state.last_click:
            st.session_state.last_click = coords
            cx, cy = coords["x"] // CELL, coords["y"] // CELL
            if in_bounds(cx, cy):
                if tool == "npc":
                    st.session_state.npc = (cx, cy)
                    st.session_state.grid[cy][cx] = EMPTY
                elif tool == "player":
                    st.session_state.player = (cx, cy)
                    st.session_state.grid[cy][cx] = EMPTY
                else:
                    mapping = {"empty": EMPTY, "tree": TREE, "house": HOUSE, "river": RIVER, "wall": WALL}
                    st.session_state.grid[cy][cx] = mapping[tool]
                recompute()
                st.rerun()

    b1, b2, b3 = st.columns(3)
    b1.button("🎲 Random Map", on_click=random_map, use_container_width=True)
    b2.button("🧽 Clear Map", on_click=clear_map, use_container_width=True)
    b3.button("🧱 Preset: One-way Corridor", on_click=corridor_preset, use_container_width=True)

    st.markdown(
        """
        **Legenda:** 🧹 Empty (cost 1) · 🌲 Tree (blocked) · 🏠 House (blocked) ·
        🧱 Wall/Tembok (blocked) · 🌊 River (cost 4) · 🟣 Expanded node · 🟡 Jalur solusi
        """
    )
    st.caption(
        "Jalur solusi sengaja diwarnai **kuning** (bukan hijau) supaya tidak ketuker "
        "sama warna terrain lain di peta saat overlay-nya aktif."
    )

with st.expander("📄 Catatan untuk laporan — ringkasan cara kerja search()"):
    st.markdown(
        """
Setiap node punya **g(n)** = biaya nyata dari NPC ke node itu (diakumulasi lewat `came_from`),
dan **h(n)** = estimasi jarak ke Player dari heuristik yang dipilih.
`heapq` selalu mem-pop node dengan **f(n) = g(n) + h(n)** terkecil.

- **UCS**: `h(n)` dipaksa 0 → priority = g(n) saja → lengkap & optimal, tapi meng-expand
  lebih banyak node (nyari ke segala arah tanpa "insting" ke arah goal).
- **A\\***: priority = g(n) + h(n) → optimal **selama** h(n) admissible (tidak pernah
  overestimate) → biasanya expand jauh lebih sedikit node daripada UCS untuk hasil yang sama.

**Kotak ungu vs kotak kuning — apa bedanya?**
- 🟣 **Ungu** = `expanded_order`, yaitu *semua* node yang sempat di-`heappop()` dan diproses
  algoritma selama pencarian berlangsung — termasuk cabang yang ternyata jalan buntu / tidak
  jadi dipakai. Ini yang dipakai buat hitung **Nodes Expanded**.
- 🟡 **Kuning** = `path`, hasil `reconstructPath()` — jalur *akhir* dari NPC ke Player yang
  didapat dengan menelusuri balik `came_from` dari goal sampai start. Ini **bukan** semua
  node ungu, cuma satu rute terpendek/termurah di antaranya.

Tombol **▶ Play** sengaja menunda kemunculan overlay: pertama animasi reveal urutan node
ungu (biar kelihatan urutan `heappop()`-nya), baru di frame terakhir jalur kuning muncul.
Setelah kamu edit peta / pindah NPC-Player / ganti algoritma, overlay disembunyikan lagi
sampai kamu pencet Play — supaya jelas kapan hasil yang ditampilkan itu "baru" vs "lama".

Coba preset **"One-way Corridor"**, lalu bandingkan UCS vs A* — keduanya sama-sama optimal
(karena heuristiknya admissible), tapi A* akan menunjukkan jumlah **Nodes Expanded** yang
jauh lebih sedikit di tabel perbandingan.
        """
    )
    st.code(
        '''priority = {
    "ucs":   g(n),          # h(n) dipaksa 0
    "astar": g(n) + h(n),
}[algo]''',
        language="python",
    )
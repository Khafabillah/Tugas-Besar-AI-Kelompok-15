# Laporan Adversarial Search: Duel NPC di Hex Arena

## 1. Pendahuluan

Proyek ini menerapkan pencarian adversarial untuk memilih aksi NPC dalam duel turn-based. NPC menggunakan Minimax sebagai dasar pengambilan keputusan, dengan Alpha-Beta untuk memangkas cabang pencarian. Proyek juga membandingkan beberapa fungsi evaluasi, urutan ekspansi aksi, kedalaman pencarian, Early Stop, dan Expectimax.

Arena heksagon menjadi lingkungan permainan dan pemicu dimulainya battle. Fokus eksperimen adalah keputusan NPC dalam fase battle. Karena itu, hasil Lab perlu ditafsirkan sebagai hasil simulasi battle melawan bot, bukan sebagai evaluasi seluruh permainan melawan pemain manusia.

## 2. Deskripsi PEAS

PEAS menjelaskan tugas agen melalui ukuran performa, lingkungan, aktuator, dan sensor.

| Komponen | Deskripsi |
|---|---|
| **Performance measure** | Win rate NPC, margin HP pada akhir simulasi, frekuensi draw/escape, dan distribusi aksi NPC. Biaya komputasi diukur terpisah melalui jumlah node dan waktu per keputusan. |
| **Environment** | Duel turn-based di arena heksagon. Battle dimulai ketika NPC dan player berjarak paling jauh 2 hex, tidak berada di safezone, dan tidak terhalang pilar pada garis pandang. Battle deterministik secara default; opsi akurasi acak memungkinkan serangan meleset. |
| **Actuators** | Dalam battle: `attack`, `power_attack`, `defend`, `potion`, dan `teleport` sesuai aksi legal. Dalam eksplorasi: NPC bergerak mengejar player. Setelah NPC teleport, NPC pulih di safezone sampai HP penuh lalu kembali mencari player. |
| **Sensors** | Untuk pencarian battle: HP, jumlah potion, status defend, cooldown, jatah teleport, giliran, dan ply kedua pihak. Untuk eksplorasi: posisi hex, jarak, safezone, pilar/garis pandang, dan lokasi potion. `Engine.search` hanya menerima state battle; persepsi peta dipakai oleh UI. |

Ukuran performa pada tabel eksperimen tidak semuanya mengukur hal yang sama. Win rate dan margin HP mengukur hasil simulasi, sedangkan node dan waktu mengukur biaya pencarian. Keduanya dibahas secara terpisah.

## 3. Formulasi Masalah

| Elemen | Definisi |
|---|---|
| **State** | `(player_hp, npc_hp, player_potions, npc_potions, player_defending, npc_defending, player_cd, npc_cd, player_teleport, npc_teleport, escaped, turn, ply)` |
| **Pemain** | NPC = MAX dan player = MIN. Keduanya bergiliran. Search dimulai dari aktor yang tercatat pada `state.turn`. |
| **Aksi** | `attack` memberikan 18 damage; `power_attack` memberikan 32 damage dan memiliki cooldown 2 giliran; `defend` mengurangi damage serangan berikutnya sebesar 60% serta memulihkan 4 HP; `potion` memulihkan 30 HP; `teleport` mengakhiri battle. HP maksimum 100. |
| **Branching factor** | Maksimal 4. Teleport menggantikan defend ketika HP aktor ≤35 dan jatah teleport masih ada. Potion hanya tersedia jika stoknya ada; power attack hanya tersedia jika cooldown nol. |
| **Transition** | `Engine.applyAction(state, actor, action, hit)` menghasilkan state baru. Pada mode probabilistik, `hit=false` berarti serangan meleset. |
| **Terminal test** | Battle berakhir ketika `escaped` terisi, salah satu pihak memiliki HP ≤0, atau `ply ≥40`. |
| **Utility** | Dari sudut pandang NPC: menang `1000 + npc_hp`; kalah `−1000 − player_hp`; keduanya 0 HP bernilai 0; escape bernilai `−150`; seri karena batas ply bernilai `npc_hp − player_hp`. Escape mengakhiri battle tanpa menetapkan pemenang pada UI. |
| **Evaluation function** | Pada state non-terminal di batas kedalaman: `material = npc_hp − player_hp`; `resource = (npc_hp − player_hp) + 6·(npc_potions − player_potions) + bonus kesiapan cooldown`; `aggressive = 1.3·npc_hp − 1.8·player_hp`; `defensive = 1.8·npc_hp − 1.2·player_hp + 5·npc_potions`. |

### Asumsi

1. Battle adalah permainan zero-sum dengan informasi sempurna.
2. Minimax dan Alpha-Beta mengasumsikan aksi lawan dipilih secara optimal. Expectimax memodelkan pilihan lawan sebagai rata-rata seragam atas aksi legalnya.
3. Akurasi `attack` adalah 90% dan `power_attack` 70% pada mode probabilistik. Expectimax memperhitungkan peluang hit/miss; Minimax dan Alpha-Beta memperlakukan serangan sebagai hit saat melakukan search.
4. Defend berlaku untuk serangan berikutnya saja dan tidak menumpuk.
5. Safezone mencegah battle dimulai dan memulihkan 10 HP per langkah eksplorasi. Setelah teleport, NPC masuk safezone, memulihkan HP sampai penuh, lalu kembali mengejar player. Perilaku pemulihan ini berada di UI, di luar pohon search battle.
6. Pilar menghalangi gerakan dan garis pandang. NPC dan player tidak dapat memulai battle ketika salah satunya berada di safezone.
7. Lab mengakhiri satu simulasi ketika teleport terjadi. Dengan demikian, outcome Lab `escape` berarti battle berakhir; Lab tidak mengukur pengejaran ulang setelah pemulihan.

## 4. Implementasi

`engine.js` berisi state, aksi, transisi, terminal test, utility, evaluation function, dan pencarian. `ui.js` menangani arena, input, battle, serta debug overlay. `lab.js` menjalankan simulasi menggunakan engine yang sama.

Minimax memilih nilai maksimum pada giliran NPC dan minimum pada giliran player. Alpha-Beta menggunakan batas α dan β untuk memangkas cabang ketika `β ≤ α`; pada state, depth, dan evaluasi yang sama, pruning seharusnya mempertahankan nilai root Minimax. Early Stop menjalankan iterative deepening dan mengembalikan hasil dari kedalaman terakhir yang selesai sebelum batas node tercapai. Expectimax merata-ratakan aksi pada node lawan dan menghitung peluang hit/miss.

## 5. Rancangan Eksperimen

Semua tabel yang diberikan memakai `N=16`. Tidak ada random seed tetap, sehingga hasil yang menggunakan bot random, state acak, atau akurasi acak dapat berubah pada run berikutnya.

| Eksperimen | Konfigurasi dan ukuran |
|---|---|
| **E1** | Minimax vs Alpha-Beta pada state hasil permainan acak yang sedang bergiliran NPC; depth 2, 4, 6, 8; node rata-rata dan kecocokan nilai root. |
| **E2/E5** | Alpha-Beta depth 4 dengan empat evaluation function melawan bot random, greedy, dan smart; win/loss/draw/escape, margin HP, ply, dan distribusi aksi. E2 dan E5 digabung dalam satu tabel. |
| **E3** | Alpha-Beta pada state sampel dan depth 2, 4, 6, 8; membandingkan urutan fixed, best-first, dan worst-first melalui node rata-rata. |
| **E4** | Alpha-Beta dengan evaluasi resource pada depth 1–6 melawan greedy dan smart; win rate, margin HP, node per keputusan, dan waktu per keputusan. |
| **E6** | Minimax, Alpha-Beta, Alpha-Beta + Early Stop (budget 200 node), dan Expectimax pada depth 4; melawan random/smart dalam kondisi serangan deterministik dan acak. |

Bot `random` memilih aksi legal secara acak. Bot `greedy` menyerang dan memakai potion saat HP rendah. Bot `smart` memilih aksi menggunakan pencarian Alpha-Beta depth 2, sehingga merupakan lawan pendekatan, bukan agen optimal.

## 6. Hasil Eksperimen

### 6.1 E1 — Minimax vs Alpha-Beta

| Depth | Node Minimax | Node Alpha-Beta | Penghematan (rasio) | Nilai root identik? |
|---:|---:|---:|---:|---|
| 2 | 16 | 14 | 1.14× | Ya |
| 4 | 171 | 88 | 1.94× | Ya |
| 6 | 1.782 | 540 | 3.30× | Ya |
| 8 | 17.860 | 2.756 | 6.48× | Ya |

### 6.2 E2/E5 — Fungsi evaluasi dan perilaku NPC

| Evaluasi | Lawan | NPC menang | NPC kalah | Seri | NPC/lawan kabur | Δ HP rata-rata | Rata-rata ply | Attack | Power | Defend | Potion | Teleport |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| material | random | 13% | 0% | 75% | 13% | +21.2 | 38.3 | 33% | 15% | 41% | 10% | 1% |
| material | greedy | 0% | 0% | 0% | 100% | −38.8 | 18.0 | 33% | 0% | 33% | 22% | 11% |
| material | smart | 0% | 0% | 0% | 100% | −24.0 | 26.0 | 38% | 8% | 31% | 15% | 8% |
| resource | random | 6% | 0% | 75% | 19% | +27.8 | 37.4 | 27% | 18% | 43% | 11% | 1% |
| resource | greedy | 0% | 0% | 0% | 100% | −52.4 | 22.0 | 18% | 0% | 55% | 18% | 9% |
| resource | smart | 0% | 0% | 0% | 100% | −32.4 | 36.0 | 56% | 0% | 28% | 11% | 6% |
| aggressive | random | 0% | 0% | 94% | 6% | +32.7 | 39.8 | 28% | 17% | 45% | 10% | 0% |
| aggressive | greedy | 0% | 0% | 0% | 100% | −32.0 | 12.0 | 50% | 0% | 0% | 33% | 17% |
| aggressive | smart | 0% | 0% | 0% | 100% | −32.0 | 12.0 | 50% | 0% | 0% | 33% | 17% |
| defensive | random | 0% | 0% | 88% | 13% | +37.0 | 39.4 | 20% | 25% | 45% | 10% | 0% |
| defensive | greedy | 100% | 0% | 0% | 0% | +3.2 | 20.0 | 20% | 30% | 30% | 20% | 0% |
| defensive | smart | 0% | 0% | 100% | 0% | −31.6 | 40.0 | 15% | 10% | 65% | 10% | 0% |

Persentase aksi adalah bagian dari seluruh aksi NPC yang tercatat, bukan persentase pertandingan. Kolom “NPC/lawan kabur” menggabungkan siapa pun yang melakukan teleport; tabel ini tidak membedakan pihak yang kabur.

### 6.3 E3 — Urutan aksi

| Depth | Urutan tetap | Best-first | Worst-first |
|---:|---:|---:|---:|
| 2 | 13 | 11 | 15 |
| 4 | 86 | 59 | 140 |
| 6 | 475 | 245 | 1.170 |
| 8 | 2.357 | 1.106 | 7.759 |

### 6.4 E4 — Kedalaman pencarian

| Depth | Menang vs greedy | Menang vs smart | Node/keputusan | ms/keputusan |
|---:|---:|---:|---:|---:|
| 1 | 100% (Δ+10.0) | 0% (Δ+12.0) | 4 | 0.00 |
| 2 | 100% (Δ+12.0) | 0% (Δ+4.0) | 13 | 0.00 |
| 3 | 0% (Δ−22.0) | 0% (Δ−22.0) | 40 | 0.02 |
| 4 | 0% (Δ−52.4) | 0% (Δ−32.4) | 73 | 0.03 |
| 5 | 100% (Δ+6.8) | 0% (Δ+2.4) | 235 | 0.07 |
| 6 | 100% (Δ+2.0) | 0% (Δ−44.8) | 468 | 0.14 |

Node dan waktu per keputusan pada tabel ini dihitung dari pertandingan melawan bot smart. Waktu 0.00 ms adalah hasil pembulatan tampilan, bukan bukti bahwa pencarian tidak memerlukan waktu.

### 6.5 E6 — Algoritma pada lingkungan deterministik dan probabilistik

| Algoritma | Deterministik vs random | Deterministik vs smart | Akurasi acak vs random | Akurasi acak vs smart |
|---|---:|---:|---:|---:|
| Minimax | 0% (Δ+37.0) | 0% (Δ−32.4) | 0% (Δ+25.7) | 0% (Δ−17.6) |
| Alpha-Beta | 0% (Δ+28.1) | 0% (Δ−32.4) | 0% (Δ+21.3) | 0% (Δ−11.8) |
| Alpha-Beta + Early Stop (≤200 node) | 0% (Δ+33.1) | 0% (Δ−32.4) | 0% (Δ+48.0) | 0% (Δ−10.6) |
| Expectimax | 50% (Δ+36.6) | 0% (Δ−70.0) | 38% (Δ+45.0) | 0% (Δ−6.5) |

“Deterministik” di sini berarti hasil serangan selalu hit; lawan `random` tetap memilih aksi secara acak. Pada pencarian Expectimax, peluang hit/miss tetap dimodelkan meskipun kondisi pertandingan deterministik.

## 7. Pembahasan

### E1: pruning Alpha-Beta

Nilai root Minimax dan Alpha-Beta identik pada semua depth yang diuji. Rasio node Minimax terhadap Alpha-Beta meningkat dari 1.14× pada depth 2 menjadi 6.48× pada depth 8. Pengurangan node sekitar 12.5%, 48.5%, 69.7%, dan 84.6% berturut-turut untuk depth 2, 4, 6, dan 8. Hasil ini sesuai dengan tujuan Alpha-Beta: mempertahankan keputusan sambil mengurangi jumlah node, dengan manfaat pruning yang makin terlihat pada depth lebih besar.

### E2/E5: evaluasi dan perilaku NPC

Hasil berbeda menurut lawan. Melawan random, material menghasilkan win rate tertinggi (13%), sedangkan defensive menghasilkan margin HP tertinggi (+37.0) tetapi mayoritas hasilnya seri atau escape. Margin HP positif tidak otomatis berarti NPC menang.

Melawan greedy, evaluasi defensive menghasilkan 100% kemenangan dengan margin +3.2. Tiga evaluasi lain berakhir 100% pada kategori kabur, dengan margin HP negatif. Melawan smart, semua evaluasi memiliki win rate 0%; defensive berakhir seri pada seluruh pertandingan dengan rata-rata 40 ply dan distribusi defend 65%, sedangkan evaluasi lainnya berakhir pada kategori kabur. Karena kolom kabur tidak mengidentifikasi siapa yang teleport, hasil itu tidak dapat ditafsirkan sebagai 100% NPC kabur.

Distribusi aksi menunjukkan defensive lebih sering memilih defend, terutama melawan smart. Aggressive melawan greedy dan smart mencatat attack 50%, potion 33%, dan teleport 17%, dengan rata-rata 12 ply. Ini menunjukkan pola aksi yang lebih ofensif pada run ini, tetapi tidak menghasilkan kemenangan pada sampel tersebut.

### E3: urutan ekspansi aksi

Best-first mengunjungi node paling sedikit pada semua depth. Pada depth 8, Best-first mengunjungi 1.106 node, dibanding 2.357 untuk urutan tetap dan 7.759 untuk Worst-first. Dibanding urutan tetap, pengurangan node Best-first naik dari sekitar 15% pada depth 2 menjadi sekitar 53% pada depth 8. Worst-first memperlambat pruning karena cabang yang kurang menjanjikan diperiksa lebih dulu.

### E4: pengaruh kedalaman

Biaya pencarian meningkat dari 4 node per keputusan pada depth 1 menjadi 468 pada depth 6. Win rate melawan greedy tidak naik secara monoton: 100% pada depth 1–2, 0% pada depth 3–4, lalu 100% pada depth 5–6. Melawan smart, win rate 0% pada semua depth, meskipun margin HP positif pada depth 1, 2, dan 5. Tabel E4 tidak menampilkan pecahan draw dan escape, jadi hasil non-win itu tidak dapat dijelaskan lebih spesifik dari tabel ini saja.

Hasil tersebut menunjukkan bahwa pencarian lebih dalam menambah biaya dan tidak otomatis menaikkan win rate. Evaluation function terbatas, interaksi aksi dan cooldown, serta efek horizon dapat membuat pilihan pada suatu depth berbeda dari pilihan yang efektif dalam pertandingan penuh.

### E6: algoritma dan akurasi serangan

Melawan random, Expectimax menghasilkan win rate 50% pada kondisi deterministik dan 38% pada kondisi akurasi acak. Tiga algoritma lain mencatat win rate 0% pada kedua kondisi tersebut, walaupun margin HP-nya positif. Karena E6 hanya menampilkan win rate dan margin, kategori hasil selain menang tidak dapat dipisahkan di tabel.

Melawan smart, tidak ada algoritma yang mencatat kemenangan. Dalam kondisi deterministik, margin Expectimax (−70.0) lebih rendah daripada algoritma lain. Pada kondisi akurasi acak, margin Expectimax adalah −6.5, tetapi win rate tetap 0%. Ini mendukung kesimpulan terbatas bahwa Expectimax tampak lebih cocok melawan pilihan acak pada sampel ini; hasilnya tidak menunjukkan keunggulan terhadap bot smart.

Perbandingan hasil pertandingan pada E6 memakai batch yang memiliki randomness, sehingga perbedaan margin antarbaris tidak membuktikan bahwa Minimax dan Alpha-Beta memberi nilai root berbeda. E1 membandingkan keduanya pada state yang sama dan menunjukkan nilai root identik. Selain itu, tabel E6 tidak mencantumkan node atau depth efektif Early Stop; efisiensi budget 200 node perlu dilaporkan dari metrik node/reached depth tersendiri, misalnya overlay pada state yang sama.

## 8. Kesimpulan

Pada state yang sama, Alpha-Beta menghasilkan nilai root yang identik dengan Minimax dan mengurangi node lebih besar pada depth yang lebih tinggi. Best-first paling hemat node dalam eksperimen urutan aksi, sedangkan Worst-first menghasilkan node terbanyak. Penambahan depth meningkatkan biaya pencarian secara nyata, tetapi tidak menjamin win rate lebih tinggi.

Evaluation function memengaruhi pola aksi dan hasil melawan bot yang berbeda. Dalam sampel ini, defensive berhasil melawan greedy tetapi tidak menang melawan smart. Expectimax memiliki win rate tertinggi melawan random, tetapi tidak menghasilkan kemenangan melawan smart. Kesimpulan tersebut berlaku untuk konfigurasi dan sampel yang diuji, bukan jaminan performa pada semua pertandingan.

## 9. Keterbatasan dan catatan metodologi

1. `N=16` merupakan sampel kecil dan beberapa eksperimen memakai randomness tanpa seed tetap. Hasil sebaiknya diulang dan dilaporkan sebagai rentang atau rata-rata beberapa run.
2. Bot smart adalah lawan buatan dengan Alpha-Beta depth 2, bukan lawan optimal atau manusia.
3. Lab memulai simulasi langsung dari state battle dan tidak memasukkan fase eksplorasi, pickup potion di arena, safezone, pilar, maupun garis pandang.
4. Teleport mengakhiri `playMatch` di Lab. Pemulihan NPC sampai HP penuh dan pengejaran ulang yang terjadi di game tidak dihitung sebagai bagian dari hasil E1–E6. Karena itu, win/escape pada tabel adalah hasil per battle.
5. Kolom `NPC/lawan kabur` pada E2/E5 tidak memisahkan pihak yang teleport. E4 dan E6 juga tidak menampilkan seluruh kategori hasil, sehingga margin HP saja tidak cukup untuk menentukan apakah pertandingan seri atau berakhir karena escape.
6. E6 membandingkan win rate dan margin, bukan biaya pencarian. Untuk menyimpulkan penghematan Early Stop, perlu node count dan reached depth pada state yang sama.
7. Waktu per keputusan bergantung pada perangkat dan pembulatan tampilan.

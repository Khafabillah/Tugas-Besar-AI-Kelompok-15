# Laporan Proyek: Simulasi Keamanan Tribun dengan CSP, Knowledge Base, dan Planning

**Tanggal:** 17 November 2026  
**Konteks:** tugas Tahap 4 pada materi Logic & Representasi Pengetahuan

## Ringkasan

Proyek memodelkan pembagian penonton pada 16 sub-zona stadion sebagai *Constraint Satisfaction Problem* (CSP). Delapan solver mencari penempatan yang memenuhi aturan keselamatan. Perluasan Tahap 4 menambahkan NPC representatif pada zona yang telah terisi, knowledge base (KB) terpisah untuk menyimpulkan interaksi mereka, overlay jejak inferensi, dan planner yang menyusun rute terpendek pada graf tribun.

Eksperimen headless menjalankan delapan mode pada dua skenario, masing-masing dengan urutan nilai `asli` dan `tamu_dulu`, menggunakan seed Min-Conflicts `42`. Seluruh 32 run menghasilkan assignment valid. Hasil tiap urutan, mode, dan skenario tercantum di bawah.

## 1. Ruang masalah

### Variabel dan domain

Terdapat 16 variabel, satu untuk setiap zona tribun:

`X = {Royal_Box, VIP_Lounge, Press_Box, Komentator, Difabel_B, Reguler_B, Skybox, Keluarga, Ekonomi_Atas, Difabel_T, Home_Core, Ekonomi_US, Transit, Away_Utama, Buffer_Kiri, Buffer_Kanan}`

Domain kategori penonton:

`D = {Tuan_Rumah, Tamu, VIP, Media, Netral}`

Domain efektif tiap zona dibatasi lagi oleh aturan unary. Misalnya, `Royal_Box` hanya menerima `VIP`, `Press_Box` hanya menerima `Media`, dan `Away_Utama` pada skenario standar hanya menerima `Tamu`.

### Constraint

Assignment `A` valid jika setiap zona mendapat nilai dari domainnya dan memenuhi semua constraint berikut:

1. **Unary/domain:** `A(x) ∈ D_s(x)`, dengan `D_s` domain yang ditetapkan oleh skenario `s`.
2. **Larangan bertetangga:** untuk setiap sisi fisik `Adjacent(x,y)`, pasangan `Tuan_Rumah`–`Tamu` dilarang.
3. **Perlindungan zona premium/media:** `Tamu` tidak boleh bertetangga dengan `VIP` atau `Media`.
4. **Batas jumlah:** paling banyak satu zona boleh berisi `Tamu`.

Secara ringkas, aturan global terakhir dapat ditulis:

`Σ_x [A(x) = Tamu] ≤ 1`

Jika `Assigned(z,g)` berarti zona `z` mendapat kelompok `g`, dan `Allowed_s(z,g)` berarti kelompok tersebut diizinkan oleh skenario `s`, constraint CSP dapat dinyatakan:

- `∀z: ∃!g ∈ D, Assigned(z,g)` (setiap zona mendapat tepat satu kelompok)
- `∀z,g: Assigned(z,g) → Allowed_s(z,g)`
- `∀z,z': Adjacent(z,z') → ¬(Assigned(z,Tuan_Rumah) ∧ Assigned(z',Tamu))`
- `∀z,z': Adjacent(z,z') → ¬(Assigned(z,Tamu) ∧ (Assigned(z',VIP) ∨ Assigned(z',Media)))`
- `|{z : Assigned(z,Tamu)}| ≤ 1`

Graf ketetanggaan berbentuk cincin yang mengikuti susunan tribun. Skenario **standar** memiliki banyak zona terkunci oleh aturan unary; skenario **longgar** memberi lebih banyak pilihan untuk menampilkan proses pencarian dan pruning.

## 2. Knowledge base dan definisi logikanya

### Vocabulary

Fakta KB dibangun dari assignment yang sedang terlihat:

- `At(npc, zona)`: NPC berada di zona tersebut.
- `Role(npc, kelompok)`: kelompok penonton NPC.
- `Adjacent(zona1, zona2)`: kedua zona bertetangga pada graf stadion.
- `AwayFromTransit(npc)`: NPC tidak sedang berada di Transit.
- `Interaction(npc1, npc2, jenis)`: interaksi yang disimpulkan.

Setiap zona yang sudah terisi diwakili satu NPC bernama `NPC-01` sampai `NPC-16`. Ini adalah representasi kelompok penghuni zona, bukan karakter dengan identitas atau atribut individual.

### Aturan Horn

KB menyimpan aturan sebagai implikasi Horn dan berada terpisah di `knowledge_base.py`.

| Aturan | Kondisi | Kesimpulan |
|---|---|---|
| R1 | NPC Tuan Rumah bertetangga dengan NPC Tamu | Peringatan keamanan |
| R2 | NPC Tamu bertetangga dengan NPC VIP | Pengawalan |
| R3 | NPC Tamu bertetangga dengan NPC Media | Pengaturan jalur liputan/pengawalan |
| R4 | NPC Media bertetangga dengan NPC VIP | Wawancara |
| R5 | Dua NPC dengan kelompok yang sama bertetangga | Saling menyapa |
| R6 | Pengunjung Netral berada di luar Transit dan ada NPC Netral di Transit | Pengunjung menuju meja informasi untuk bertanya arah |

Aturan lengkap dalam notasi predikat:

- **R1:** `Role(h, Tuan_Rumah) ∧ At(h, z_h) ∧ Role(a, Tamu) ∧ At(a, z_a) ∧ Adjacent(z_h, z_a) → Interaction(h, a, ALERT)`
- **R2:** `Role(a, Tamu) ∧ At(a, z_a) ∧ Role(v, VIP) ∧ At(v, z_v) ∧ Adjacent(z_a, z_v) → Interaction(a, v, ESCORT)`
- **R3:** `Role(a, Tamu) ∧ At(a, z_a) ∧ Role(m, Media) ∧ At(m, z_m) ∧ Adjacent(z_a, z_m) → Interaction(a, m, ESCORT)`
- **R4:** `Role(m, Media) ∧ At(m, z_m) ∧ Role(v, VIP) ∧ At(v, z_v) ∧ Adjacent(z_m, z_v) → Interaction(m, v, INTERVIEW)`
- **R5:** `Role(a, g) ∧ At(a, z_a) ∧ Role(b, g) ∧ At(b, z_b) ∧ Adjacent(z_a, z_b) → Interaction(a, b, SAY_HELLO)`
- **R6:** `Role(p, Netral) ∧ AwayFromTransit(p) ∧ At(i, Transit) ∧ Role(i, Netral) → Interaction(p, i, ASK_DIRECTIONS)`

Variabel huruf kecil pada aturan adalah variabel logika yang dicocokkan dengan konstanta fakta. R1–R6 merupakan aturan positif: tidak menggunakan negasi saat inferensi. Batas “di luar Transit” pada R6 disiapkan sebagai fakta `AwayFromTransit(p)` ketika NPC ditempatkan.

### Proses inferensi

`logic_engine.py` menerapkan *forward chaining* untuk aturan positif. Jika `F₀` adalah fakta awal dan `KB` adalah kumpulan aturan, proses menambahkan kesimpulan yang premisnya sudah terpenuhi:

`Fₖ₊₁ = Fₖ ∪ {kesimpulan(θ) | aturan KB cocok dengan fakta Fₖ menggunakan substitusi θ}`

Proses berhenti saat tidak ada fakta baru. Setiap fakta turunan menyimpan nama aturan dan premis yang memicunya; overlay menampilkan jejak tersebut.

## 3. Automated planning

`planner.py` menggunakan pencarian breadth-first search (BFS) pada graf zona untuk menyusun rencana terpendek menuju NPC pasangan interaksi.

- **State:** `(zona_NPC, interaksi_selesai)`.
- **Aksi `Move(z1,z2)`:** berlaku jika NPC berada di `z1` dan `Adjacent(z1,z2)` benar; efeknya NPC berpindah ke `z2`.
- **Aksi `Interact`:** berlaku ketika NPC mencapai zona pasangan; efeknya menandai interaksi selesai.
- **Goal:** interaksi yang disimpulkan KB berhasil dilakukan.

Planner membuat *rencana* yang ditampilkan di overlay; pada versi ini gerakan tidak dianimasikan dan tidak mengubah assignment CSP.

## 4. Struktur implementasi

| Berkas | Peran |
|---|---|
| `config.py`, `csp_model.py` | Domain, zona, skenario, graf, dan constraint CSP |
| `solvers.py`, `heuristics.py`, `inference.py` | Min-Conflicts, Backtracking, MRV, LCV, Forward Checking, dan AC-3 |
| `logic_engine.py` | Mesin inferensi forward chaining generik |
| `knowledge_base.py` | Aturan interaksi NPC yang terpisah dari UI |
| `npc_logic.py` | Membentuk fakta dari assignment, menjalankan KB, dan menyiapkan rencana |
| `planner.py` | Pencarian rute dan urutan aksi BFS |
| `events.py`, `app.py`, `renderer.py` | Data tampilan, loop Pygame, kontrol, dan overlay |

Overlay dibuka atau ditutup dengan tombol **I** atau tombol overlay pada panel kanan. Roda mouse menelusuri fakta, aturan, jejak inferensi, interaksi, dan rencana. **Esc** menutup overlay; saat overlay tertutup, Esc keluar dari aplikasi.

## 5. Metode run

Run dilakukan langsung pada generator solver yang dipakai aplikasi, dengan `trace=False` agar proses dapat dihitung tanpa jeda animasi. Ini bukan test suite dan tidak menjalankan jendela Pygame.

- Python `3.12.10`
- Skenario: `standar` dan `longgar`
- Mode: 1–8 pada masing-masing skenario
- Seed Min-Conflicts: `42`
- Urutan nilai statis: `asli` dan `tamu_dulu`
- Semua hasil dinyatakan valid jika assignment lengkap dan total konflik akhir nol.

Urutan `asli` adalah `[Tuan_Rumah, Tamu, VIP, Media, Netral]`; urutan `tamu_dulu` adalah `[Tamu, Tuan_Rumah, VIP, Media, Netral]`. Min-Conflicts tidak menggunakan urutan nilai statis.

`Clash` dan `Backtrack` pada Backtracking menghitung percobaan assignment yang ditolak dan pembatalannya. Pada Min-Conflicts, iterasi menghitung perubahan nilai; konflik akhirnya dilaporkan terpisah. Karena itu angka iterasi Min-Conflicts tidak sebanding langsung dengan iterasi Backtracking.

### Hasil skenario standar

| Mode | Berhasil | Iterasi | Clash / Backtrack | FC cek / hapus | AC-3 cek / hapus | Cek constraint |
|---|---:|---:|---:|---:|---:|---:|
| 1 Min-Conflicts | Ya; konflik akhir 0 | 0 | — | — | — | 2.579 |
| 2 Naif + NC | Ya | 16 | 0 / 0 | 0 / 0 | 0 / 0 | 468 |
| 3 MRV | Ya | 16 | 0 / 0 | 0 / 0 | 0 / 0 | 442 |
| 4 LCV | Ya | 16 | 0 / 0 | 0 / 0 | 0 / 0 | 972 |
| 5 FC | Ya | 16 | 0 / 0 | 0 / 0 | 0 / 0 | 1.476 |
| 6 MAC / AC-3 | Ya | 16 | 0 / 0 | 0 / 0 | 0 / 0 | 1.476 |
| 7 MRV + LCV | Ya | 16 | 0 / 0 | 0 / 0 | 0 / 0 | 946 |
| 8 MRV + LCV + MAC | Ya | 16 | 0 / 0 | 0 / 0 | 0 / 0 | 1.954 |

### Hasil skenario longgar

| Mode | Berhasil | Iterasi | Clash / Backtrack | FC cek / hapus | AC-3 cek / hapus | Cek constraint |
|---|---:|---:|---:|---:|---:|---:|
| 1 Min-Conflicts | Ya; konflik akhir 0 | 2 | — | — | — | 521 |
| 2 Naif + NC | Ya | 20 | 4 / 4 | 0 / 0 | 0 / 0 | 654 |
| 3 MRV | Ya | 20 | 4 / 4 | 0 / 0 | 0 / 0 | 622 |
| 4 LCV | Ya | 16 | 0 / 0 | 0 / 0 | 0 / 0 | 2.237 |
| 5 FC | Ya | 16 | 0 / 0 | 128 / 11 | 0 / 0 | 3.161 |
| 6 MAC / AC-3 | Ya | 16 | 0 / 0 | 0 / 0 | 273 / 11 | 4.572 |
| 7 MRV + LCV | Ya | 16 | 0 / 0 | 0 / 0 | 0 / 0 | 2.205 |
| 8 MRV + LCV + MAC | Ya | 16 | 0 / 0 | 0 / 0 | 198 / 2 | 5.795 |

### Hasil urutan nilai `tamu_dulu`

Tabel sebelumnya memakai urutan `asli`. Berikut hasil run ulang dengan urutan kandidat yang mencoba `Tamu` sebelum `Tuan_Rumah`. Format metriknya sama.

#### Skenario standar

| Mode | Berhasil | Iterasi | Clash / Backtrack | FC cek / hapus | AC-3 cek / hapus | Cek constraint |
|---|---:|---:|---:|---:|---:|---:|
| 1 Min-Conflicts | Ya; konflik akhir 0 | 0 | — | — | — | 2.579 |
| 2 Naif + NC | Ya | 16 | 0 / 0 | 0 / 0 | 0 / 0 | 468 |
| 3 MRV | Ya | 16 | 0 / 0 | 0 / 0 | 0 / 0 | 442 |
| 4 LCV | Ya | 16 | 0 / 0 | 0 / 0 | 0 / 0 | 972 |
| 5 FC | Ya | 16 | 0 / 0 | 0 / 0 | 0 / 0 | 1.476 |
| 6 MAC / AC-3 | Ya | 16 | 0 / 0 | 0 / 0 | 0 / 0 | 1.476 |
| 7 MRV + LCV | Ya | 16 | 0 / 0 | 0 / 0 | 0 / 0 | 946 |
| 8 MRV + LCV + MAC | Ya | 16 | 0 / 0 | 0 / 0 | 0 / 0 | 1.954 |

#### Skenario longgar

| Mode | Berhasil | Iterasi | Clash / Backtrack | FC cek / hapus | AC-3 cek / hapus | Cek constraint |
|---|---:|---:|---:|---:|---:|---:|
| 1 Min-Conflicts | Ya; konflik akhir 0 | 2 | — | — | — | 521 |
| 2 Naif + NC | Ya | 27 | 11 / 11 | 0 / 0 | 0 / 0 | 834 |
| 3 MRV | Ya | 27 | 11 / 11 | 0 / 0 | 0 / 0 | 820 |
| 4 LCV | Ya | 16 | 0 / 0 | 0 / 0 | 0 / 0 | 2.237 |
| 5 FC | Ya | 16 | 0 / 0 | 128 / 11 | 0 / 0 | 3.161 |
| 6 MAC / AC-3 | Ya | 16 | 0 / 0 | 0 / 0 | 273 / 11 | 4.572 |
| 7 MRV + LCV | Ya | 16 | 0 / 0 | 0 / 0 | 0 / 0 | 2.205 |
| 8 MRV + LCV + MAC | Ya | 16 | 0 / 0 | 0 / 0 | 198 / 2 | 5.795 |

### Contoh assignment valid dari mode 8

| Zona | Standar, `asli` | Longgar, `asli` | Longgar, `tamu_dulu` |
|---|---|---|---|
| Royal Box | VIP | VIP | VIP |
| VIP Lounge | VIP | VIP | VIP |
| Press Box | Media | Media | Media |
| Komentator | Media | Media | Media |
| Difabel B | Netral | Netral | Netral |
| Reguler B | Tuan Rumah | Netral | Netral |
| Skybox | VIP | VIP | VIP |
| Keluarga | Netral | Netral | Netral |
| Ekonomi Atas | Tuan Rumah | Netral | Netral |
| Difabel T | Netral | Netral | Netral |
| Home Core | Tuan Rumah | Netral | Netral |
| Ekonomi U/S | Tuan Rumah | Netral | Netral |
| Transit | Netral | Tuan Rumah | Tuan Rumah |
| Away Utama | Tamu | Netral | Netral |
| Buffer Kiri | Netral | Tuan Rumah | Tuan Rumah |
| Buffer Kanan | Netral | Tuan Rumah | Tamu |

Semua assignment di tabel memiliki konflik akhir nol. Pada hasil standar ini KB menurunkan 11 interaksi unik. Contoh kesimpulan: NPC-03 (Media, Press Box) dapat mewawancarai NPC-02 (VIP, VIP Lounge); beberapa NPC Netral meminta arah ke NPC-13 di Transit.

Contoh rencana hasil BFS untuk NPC-05 (Difabel B) menuju NPC-13 (Transit):

1. Bergerak dari Difabel B ke Reguler B.
2. Bergerak dari Reguler B ke Transit.
3. Bertanya arah kepada NPC-13.

## 6. Pembahasan hasil

- Semua mode menemukan solusi pada kedua skenario untuk seed yang dicatat.
- Pada skenario standar, hasil metrik kedua urutan sama karena satu-satunya zona yang domainnya mengizinkan `Tamu` adalah `Away_Utama`, yang memang terkunci menjadi `Tamu`.
- Pada skenario longgar, `tamu_dulu` meningkatkan percobaan mode naif dan MRV dari 20 menjadi 27 serta clash/backtrack dari 4 menjadi 11. Keduanya lebih sering mencoba penempatan Tamu yang kemudian berkonflik.
- Min-Conflicts tidak memakai urutan nilai statis, sehingga metriknya sama untuk kedua urutan pada seed `42`. Mode LCV dan kombinasinya tetap menyelesaikan run longgar dalam 16 iterasi tanpa clash; pada hasil ini `tamu_dulu` mengubah assignment mode 4, 7, dan 8 sehingga Tamu ditempatkan di Buffer Kanan.
- Pada skenario standar, domain yang sebagian besar terkunci membuat semua mode Backtracking selesai dalam 16 percobaan tanpa konflik. AC-3 tidak menghapus nilai pada run standar karena graf constraint setelah pemangkasan unary tidak memiliki arc yang perlu diproses.
- Pada skenario longgar dengan urutan `asli`, Backtracking naif dan MRV masing-masing mengalami 4 konflik dan 4 backtrack. LCV dan kombinasi MRV+LCV menyelesaikan run ini tanpa konflik pada urutan nilai dan seed tersebut.
- Forward Checking menghapus 11 kandidat dari 128 pemeriksaan pada run longgar. AC-3 mode 6 juga menghapus 11 nilai setelah memeriksa 273 arc. Mode 8 memeriksa 198 arc dan menghapus 2 nilai.
- Min-Conflicts mendapatkan susunan legal acak sejak awal pada skenario standar (0 perubahan), dan memerlukan 2 perubahan pada skenario longgar. Hasil ini khusus untuk seed `42`; seed lain dapat memberi jumlah iterasi berbeda.
- Jumlah cek constraint menunjukkan bahwa lebih sedikit konflik tidak selalu berarti lebih sedikit operasi. Contohnya mode 8 longgar tidak melakukan backtrack, tetapi mencatat 5.795 pemeriksaan constraint karena biaya LCV dan AC-3.

## 7. Batasan model

NPC mewakili kategori penonton di satu zona, bukan karakter individual. Planner mencari rute berdasarkan adjacency zona saja; model belum memperhitungkan kapasitas, hambatan, waktu, atau pergerakan NPC lain. Hasil Min-Conflicts bergantung pada seed. Hasil eksperimen ini menunjukkan perilaku pada konfigurasi yang tercatat, bukan jaminan peringkat performa untuk semua seed atau skenario.

## 8. Cara menjalankan aplikasi

Dengan Pygame terpasang, jalankan:

```powershell
python main.py
```

Pilih solver dengan tombol `1`–`8`; `S` mengganti skenario, `I` membuka overlay KB dan planning, `Spasi` jeda, `N` melangkah saat jeda, `R` reset, dan `Esc` menutup overlay atau keluar dari aplikasi.

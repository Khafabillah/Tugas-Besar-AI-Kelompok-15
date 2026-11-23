# Skrip Video Demo Proyek Tahap 4

**Durasi target:** sekitar 7 menit 30 detik  
**Gaya:** demonstrasi aplikasi langsung, dengan penjelasan singkat saat fitur ditampilkan

> Arahan dalam tanda kurung siku adalah petunjuk visual, tidak perlu dibacakan.

## 0:00–0:25 — Pembukaan

[Tampilkan aplikasi stadion.]

Halo, di video ini saya akan mendemonstrasikan proyek simulasi keamanan tribun stadion. Saya akan menjalankan solver CSP, melihat bagaimana knowledge base menyimpulkan interaksi NPC, membuka rencana geraknya, lalu membandingkan dua algoritma pada skenario yang lebih longgar.

## 0:25–0:55 — Mengenali tampilan

[Gerakkan kursor ke peta dan panel kanan.]

Di sisi kiri ada 16 zona stadion. Warna node menunjukkan kategori penonton yang ditempatkan di sana. Garis menunjukkan zona yang bertetangga. Panel kanan berisi kontrol algoritma, metrik pencarian, hasil run, dan log.

Setiap zona merupakan variabel CSP. Nilainya adalah Tuan Rumah, Tamu, VIP, Media, atau Netral. Solver harus mematuhi domain setiap zona, aturan larangan bertetangga, dan batas paling banyak satu zona Tamu.

## 0:55–1:45 — Run pertama: solusi standar

[Tekan `+` beberapa kali untuk mempercepat animasi, lalu tekan `8`. Tunggu solver selesai.]

Saya mulai dari skenario standar dengan mode 8, yaitu MRV, LCV, dan MAC atau AC-3. MRV memilih zona dengan pilihan paling sedikit. LCV mengurutkan nilai yang paling sedikit membatasi zona lain. MAC memakai AC-3 untuk memangkas domain yang tidak punya dukungan.

[Tunjuk assignment akhir dan status solusi.]

Aplikasi sudah mengisi seluruh zona dan menandai solusi sebagai valid. Di tabel perbandingan, mode ini selesai dalam 16 percobaan tanpa clash atau backtrack. Pada skenario standar, banyak zona sudah terkunci oleh domain unary, sehingga pencarian relatif mudah.

## 1:45–3:35 — Demo knowledge base dan inferensi

[Tekan `I` untuk membuka overlay. Tunjuk kolom fakta dan aturan.]

Sekarang saya buka overlay logika dengan tombol I. Fakta di sini mengikuti assignment yang baru saja ditemukan. Contohnya, NPC-03 berada di Press Box dan berperan sebagai Media. NPC-02 berada di VIP Lounge dan berperan sebagai VIP.

Aturan interaksi disimpan terpisah dari tampilan. Misalnya, aturan R4 berbunyi: jika NPC Media dan NPC VIP berada di zona yang bertetangga, maka knowledge base menyimpulkan interaksi wawancara.

[Tunjuk bagian “Jejak Inferensi”. Scroll jika bagian tersebut belum terlihat.]

Jejak ini memperlihatkan fakta-fakta yang cocok dengan premis R4, lalu kesimpulan `Interaction` yang dihasilkan. Mesin memakai forward chaining: kesimpulan baru ditambahkan sebagai fakta, dan aturan diperiksa lagi sampai tidak ada fakta baru.

[Tunjuk daftar interaksi di kolom kanan.]

Selain wawancara, hasil run ini juga memuat sapaan antarpenonton dengan kelompok yang sama dan pengunjung Netral yang meminta arah ke meja informasi di Transit. Dengan begitu, overlay menunjukkan fakta awal, aturan yang dipakai, dan hasil inferensinya.

## 3:35–4:20 — Demo automated planning

[Scroll ke bagian “Rencana NPC”. Tunjuk rencana NPC-05 menuju Transit.]

Knowledge base menyimpulkan bahwa NPC-05 dari Difabel B ingin bertanya arah kepada NPC-13 di Transit. Planner kemudian mencari rute terpendek pada graf zona.

Rencananya adalah bergerak dari Difabel B ke Reguler B, lanjut ke Transit, lalu bertanya arah. Planner memakai BFS. Aksi bergerak hanya tersedia jika dua zona bertetangga. Di versi ini rencana ditampilkan sebagai hasil perhitungan, belum dieksekusi atau dianimasikan.

[Tekan `I` untuk menutup overlay.]

## 4:20–5:55 — Skenario longgar dan urutan `tamu_dulu`

[Tekan `S` untuk mengganti skenario. Tekan `O` satu kali untuk memilih `tamu_dulu`. Periksa label urutan di panel. Atur kecepatan sedang dengan `+` satu atau dua kali. Tekan `2`.]

Sekarang saya pindah ke skenario longgar, yang memberi lebih banyak pilihan untuk zona. Saya pilih urutan nilai `tamu_dulu`, sehingga Backtracking mencoba nilai Tamu lebih awal. Mode 2 adalah Backtracking naif dengan Node Consistency.

[Tunjuk node merah atau pesan clash ketika muncul. Jika perlu, tekan Spasi untuk jeda lalu tunjuk log; tekan Spasi lagi untuk melanjutkan.]

Di sini terlihat bahwa percobaan yang melanggar aturan dibatalkan. Pada run ini solver melakukan 27 percobaan, dengan 11 clash dan 11 backtrack, lalu tetap menemukan solusi valid.

## 5:55–6:45 — Bandingkan dengan MRV + LCV

[Setelah mode 2 selesai, tekan `7`. Tunggu sampai selesai. Tunjuk baris mode 2 dan 7 pada tabel hasil.]

Sekarang saya jalankan mode 7, yaitu MRV ditambah LCV. Pada urutan dan skenario yang sama, mode ini menyelesaikan run dalam 16 percobaan tanpa clash atau backtrack. Jadi, heuristik membantu solver menghindari beberapa pilihan yang berujung konflik pada contoh ini.

Hasil ini bukan berarti mode 7 selalu paling cepat untuk semua konfigurasi. Ini adalah hasil pada skenario dan urutan nilai yang sedang diperlihatkan.

## 6:45–7:25 — Ringkasan hasil dan penutup

[Tampilkan laporan dan sorot tabel hasil `asli` dibandingkan `tamu_dulu`.]

Perbandingan lengkap pada laporan mencakup delapan mode, dua skenario, dan dua urutan nilai, sebanyak 32 run. Semuanya menghasilkan solusi valid dengan seed Min-Conflicts 42. Pada skenario standar, urutan nilai tidak mengubah hasil karena Away Utama adalah satu-satunya zona yang dapat menerima Tamu dan nilainya terkunci. Pada skenario longgar, urutan `tamu_dulu` membuat mode naif dan MRV lebih sering mencoba penempatan yang berkonflik.

Demonstrasi ini memperlihatkan alur proyek dari pencarian assignment, inferensi interaksi NPC, sampai rencana gerak pada graf stadion. Terima kasih.

## Checklist singkat sebelum merekam

- Jalankan aplikasi dengan `python main.py`.
- Pastikan jendela cukup besar agar peta dan panel kanan terbaca.
- Mulai dari skenario standar dan mode 8 untuk menampilkan interaksi wawancara serta rute ke Transit.
- Ganti ke skenario longgar, pilih `tamu_dulu`, lalu bandingkan mode 2 dengan mode 7.
- Tabel perbandingan di aplikasi menyimpan hasil dalam skenario aktif. Gunakan laporan Markdown untuk membandingkan seluruh hasil kedua urutan nilai.

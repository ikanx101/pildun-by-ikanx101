# FIFA World Cup 2026 — Match Statistics Scraper

Proyek ini mengambil statistik pertandingan FIFA World Cup 2026 secara otomatis dari API resmi FIFA dan menyimpannya dalam format CSV.

---

## Struktur Folder

```
pildun/
├── README.md            <- Dokumentasi ini
├── perintah.txt         <- Instruksi awal proyek
└── data/
    ├── fifa_scraper.py              <- Skrip scraping utama
    └── fifa_worldcup2026_stats.csv  <- Hasil data (diperbarui setiap run)
```

---

## Cara Kerja Skrip

### 1. Ambil daftar pertandingan selesai
Skrip memanggil FIFA Calendar API untuk mendapatkan semua pertandingan Fase Grup:

```
GET https://api.fifa.com/api/v3/calendar/matches
    ?language=en&idCompetition=17&idSeason=285023&idStage=289273&count=400
```

Hanya pertandingan dengan `MatchStatus == 0` (sudah selesai / Full Time) yang diproses.

### 2. Ambil statistik per pertandingan
Untuk setiap pertandingan selesai, skrip mengambil statistik tim dari FIFA Data Hub API menggunakan `IdIFES` (ID internal FIFA):

```
GET https://fdh-api.fifa.com/v1/stats/match/{IdIFES}/teams.json
```

Endpoint ini mengembalikan 145 kategori statistik untuk masing-masing tim.

### 3. Susun data per baris per tim
Setiap pertandingan menghasilkan **2 baris** di CSV — satu untuk tim tuan rumah, satu untuk tim tamu. Kolom mencakup:

| Kelompok | Kolom |
|---|---|
| Info pertandingan | `match_id`, `date`, `stage`, `group`, `venue`, `city` |
| Info tim | `home_team`, `away_team`, `team`, `opponent`, `team_goals`, `opponent_goals` |
| 145 statistik | `Assists`, `AttemptAtGoal`, `Possession`, `Passes`, `YellowCards`, ... |
| Label hasil | `result` |

### 4. Tentukan kolom `result`
- `win` — jika `team_goals > opponent_goals`
- `not win` — jika kalah **atau** seri (draw dianggap bukan kemenangan)

### 5. Simpan ke CSV
File disimpan otomatis ke `fifa_worldcup2026_stats.csv` di **direktori kerja saat skrip dijalankan** (current working directory), sehingga lokasi output mengikuti posisi folder saat ini.

---

## Cara Menjalankan

Jalankan dari **folder root proyek** agar CSV tersimpan di sana:

```bash
python3 scraper/data/fifa_scraper.py
```

CSV akan tersimpan di direktori aktif saat skrip dijalankan (`fifa_worldcup2026_stats.csv`).

Skrip dapat dijalankan ulang kapan saja. Setiap run akan **menimpa** file CSV dengan data terbaru (termasuk pertandingan yang baru selesai).

---

## Dependensi

Library Python yang dibutuhkan (sudah tersedia di lingkungan ini):

```
requests
```

Tidak memerlukan instalasi tambahan.

---

## Catatan

- Data hanya mencakup pertandingan yang sudah **selesai** (Full Time). Pertandingan yang belum dimainkan tidak akan muncul di CSV.
- Skrip menggunakan API publik FIFA tanpa autentikasi. Jika FIFA mengubah struktur API-nya, skrip perlu disesuaikan.
- Setiap run menambahkan jeda kecil (0,3 detik) antar permintaan API untuk menghindari rate limiting.

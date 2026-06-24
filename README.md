# Pildun 2026 — Analitik & Prediksi Piala Dunia FIFA

Proyek ini menggabungkan **scraping data real-time** dari API resmi FIFA, **analitik statistik mendalam**, dan **machine learning** untuk memprediksi peluang kemenangan setiap tim di Piala Dunia FIFA 2026.

---

## Struktur Proyek

```
pildun-by-ikanx101/
│
├── update.sh                     ← 🚀 JALANKAN INI untuk update semua data
│
├── index.html                    ← Website utama (visualisasi & prediksi)
├── server.js                     ← Express server
├── package.json
│
├── fifa_worldcup2026_stats.csv   ← Data mentah hasil scraping
├── stats_data.json               ← Statistik per tim (dibaca web)
├── top_models.json               ← Hasil evaluasi model ML (dibaca web)
├── top5_predictions.json         ← Prediksi 5 besar (dibaca web)
│
├── scraper/
│   └── data/
│       └── fifa_scraper.py       ← Scraper API FIFA
│
└── prediksi/
    ├── generate_stats.py         ← Hitung statistik per tim → stats_data.json
    ├── model_klasifikasi.py      ← Evaluasi 14 model ML → top_models.json
    ├── prediksi_tim.py           ← Prediksi peluang per negara → top5_predictions.json
    ├── hasil_perbandingan_model.csv
    ├── feature_importance_rf.csv
    └── feature_importance_xgb.csv
```

---

## Cara Update (Satu Perintah)

Setelah pertandingan baru selesai, jalankan pipeline lengkap dari folder root:

```bash
bash update.sh
```

Pipeline ini berjalan **4 langkah otomatis berurutan**:

```
[1/4] Scraping data terbaru dari FIFA API
      → memperbarui fifa_worldcup2026_stats.csv

[2/4] Generate stats_data.json
      → memperbarui seluruh grafik & klasemen di website

[3/4] Training & evaluasi 14 model ML → top_models.json
      → memperbarui panel perbandingan model di website

[4/4] Rata-rata statistik per negara → LightGBM → top5_predictions.json
      → memperbarui panel prediksi 5 besar di website
```

Setelah pipeline selesai, **website langsung menampilkan data terbaru** — tidak perlu edit kode apapun.

---

## Menjalankan Website

```bash
npm start
# atau
node server.js
```

Website berjalan di `http://localhost:3000`.

---

## Dependensi

### Node.js
```bash
npm install
```

### Python
```bash
pip install scikit-learn xgboost lightgbm pandas requests
```

---

## Arsitektur Data

```
FIFA API
   │
   ▼
fifa_worldcup2026_stats.csv   (92 baris × 155 kolom)
   │
   ├──► generate_stats.py ──► stats_data.json
   │         (agregasi per tim)      (dibaca index.html)
   │
   ├──► model_klasifikasi.py ──► top_models.json
   │         (14 model, 10-fold CV)   (dibaca index.html)
   │
   └──► prediksi_tim.py ──────► top5_predictions.json
             (rata-rata per tim         (dibaca index.html)
              → LightGBM predict_proba)
```

Ketiga file JSON dibaca oleh `index.html` melalui `fetch()` — sehingga setiap kali pipeline dijalankan, website **otomatis mencerminkan data terbaru** tanpa perlu di-deploy ulang.

---

## Model Machine Learning

Target klasifikasi: apakah suatu tim **menang** atau **tidak menang** dalam satu pertandingan.

**Fitur**: 132 variabel statistik FIFA (xG, passing, pressing, sprint distance, dll.) — fitur yang langsung bocor ke label (Goals, GoalsConceded, dll.) dibuang.

**Evaluasi**: Stratified 10-fold Cross-Validation.

| Rank | Model | Accuracy | F1-Score | AUC-ROC |
|------|-------|----------|----------|---------|
| 1 | **LightGBM** | **86.00%** | 0.7448 | 0.9417 |
| 2 | XGBoost | 84.78% | 0.6881 | 0.9222 |
| 3 | Extra Trees | 81.56% | 0.6213 | 0.8847 |
| 4 | Logistic Regression | 80.56% | 0.6979 | 0.8431 |
| 5 | LDA | 80.56% | 0.6998 | 0.8583 |
| ... | *(14 model total)* | | | |

Model terbaik (**LightGBM**) digunakan untuk prediksi peluang per tim.

---

## Prediksi Saat Ini

> *Diperbarui terakhir: 24 Juni 2026 — 46 pertandingan selesai*

Probabilitas dihitung dari **rata-rata statistik** tiap tim yang dimasukkan ke model LightGBM.

| Rank | Tim | Grup | P(menang) |
|------|-----|------|-----------|
| 🥇 | 🇫🇷 France | Group I | 99.8% |
| 🥈 | 🇩🇪 Germany | Group E | 99.4% |
| 🥉 | 🇺🇸 USA | Group D | 99.2% |
| 4 | 🇳🇴 Norway | Group I | 98.9% |
| 5 | 🇦🇷 Argentina | Group J | 96.9% |

**Catatan**: Prediksi ini bersifat dinamis. Setiap pertandingan baru yang selesai akan menggeser rata-rata statistik tim — dan ranking dapat berubah setelah `bash update.sh` dijalankan.

---

## Sumber Data

- **FIFA Calendar API** — daftar pertandingan selesai  
- **FIFA Data Hub** (`fdh-api.fifa.com`) — 145 kategori statistik per tim per pertandingan  
- Tidak memerlukan autentikasi (API publik FIFA)

---

## Tentang Proyek

Dibuat oleh [ikanx101](https://ikanx101.com) · FIFA World Cup 2026

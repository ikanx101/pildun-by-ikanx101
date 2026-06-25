#!/usr/bin/env bash
# =============================================================================
# PIPELINE PILDUN 2026 — jalankan sekali untuk update semua data & prediksi
# Usage: bash update.sh
# =============================================================================

set -euo pipefail

PROJ="$(cd "$(dirname "$0")" && pwd)"
PRED="$PROJ/prediksi"
RED='\033[0;31m'; GRN='\033[0;32m'; YLW='\033[1;33m'; CYN='\033[0;36m'; NC='\033[0m'

log_step() { echo -e "\n${CYN}══════════════════════════════════════════════${NC}"; echo -e "${YLW}[$1/4] $2${NC}"; echo -e "${CYN}══════════════════════════════════════════════${NC}"; }
log_ok()   { echo -e "${GRN}✓ $1${NC}"; }
log_fail() { echo -e "${RED}✗ $1${NC}"; exit 1; }

echo -e "${YLW}"
echo "  ██████╗ ██╗██╗     ██████╗ ██╗   ██╗███╗   ██╗"
echo "  ██╔══██╗██║██║     ██╔══██╗██║   ██║████╗  ██║"
echo "  ██████╔╝██║██║     ██║  ██║██║   ██║██╔██╗ ██║"
echo "  ██╔═══╝ ██║██║     ██║  ██║██║   ██║██║╚██╗██║"
echo "  ██║     ██║███████╗██████╔╝╚██████╔╝██║ ╚████║"
echo "  ╚═╝     ╚═╝╚══════╝╚═════╝  ╚═════╝ ╚═╝  ╚═══╝"
echo -e "  FIFA World Cup 2026 — Update Pipeline${NC}"
echo ""

# ── [1/4] Scrape data terbaru dari FIFA API ──────────────────────────────────
log_step 1 "Scraping data terbaru dari FIFA API"
cd "$PROJ"
if python3 scraper/data/fifa_scraper.py; then
    ROWS=$(python3 -c "import csv; print(sum(1 for _ in open('fifa_worldcup2026_stats.csv'))-1)")
    MATCHES=$((ROWS / 2))
    log_ok "fifa_worldcup2026_stats.csv diperbarui — $MATCHES pertandingan, $ROWS baris"
else
    log_fail "Scraper gagal. Cek koneksi internet atau perubahan API FIFA."
fi

# ── [2/4] Generate stats untuk visualisasi web ──────────────────────────────
log_step 2 "Menghasilkan stats_data.json untuk visualisasi web"
cd "$PRED"
if python3 generate_stats.py; then
    TEAMS=$(python3 -c "import json; d=json.load(open('../stats_data.json')); print(len(d))")
    log_ok "stats_data.json diperbarui — $TEAMS tim (analitik web kini live)"
else
    log_fail "generate_stats.py gagal."
fi

# ── [2.5] Update angka pertandingan & tanggal di index.html ─────────────────
cd "$PROJ"
if python3 update_html.py; then
    log_ok "index.html diperbarui (angka pertandingan & tanggal)"
else
    log_fail "update_html.py gagal."
fi

# ── [3/4] Training & evaluasi model ML ──────────────────────────────────────
log_step 3 "Training & evaluasi 14 model klasifikasi ML"
cd "$PRED"
if python3 model_klasifikasi.py 2>&1 | grep -E "(Acc=|TABEL|Model dilatih|Disimpan)"; then
    BEST=$(python3 -c "import json; d=json.load(open('../top_models.json')); m=d['top3'][0]; print(f\"{m['model']} — Acc={m['accuracy']*100:.2f}%\")")
    log_ok "top_models.json diperbarui — model terbaik: $BEST"
else
    log_fail "model_klasifikasi.py gagal."
fi

# ── [4/4] Prediksi peluang per negara ───────────────────────────────────────
log_step 4 "Prediksi peluang menang per negara (rata-rata statistik → LightGBM)"
if python3 prediksi_tim.py 2>&1 | grep -E "(Top [0-9]|◀|Disimpan)"; then
    TOP1=$(python3 -c "import json; d=json.load(open('../top5_predictions.json')); t=d['top5'][0]; print(f\"{t['team']} ({t['win_probability']*100:.1f}%)\")")
    log_ok "top5_predictions.json diperbarui — peluang tertinggi: #1 $TOP1"
else
    log_fail "prediksi_tim.py gagal."
fi

# ── Summary ──────────────────────────────────────────────────────────────────
echo ""
echo -e "${GRN}══════════════════════════════════════════════════${NC}"
echo -e "${GRN}  Pipeline selesai! Semua data website diperbarui.${NC}"
echo -e "${GRN}══════════════════════════════════════════════════${NC}"
echo ""
echo "  Output files:"
echo "    fifa_worldcup2026_stats.csv   ← data mentah pertandingan"
echo "    stats_data.json               ← grafik & klasemen web"
echo "    top_models.json               ← panel perbandingan model ML"
echo "    top5_predictions.json         ← panel prediksi 5 besar"
echo ""
echo "  Buka website untuk melihat pembaruan."
echo ""

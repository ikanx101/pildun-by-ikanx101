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

# ── Pre-check: pastikan Python & dependencies aman ───────────────────────────
log_step 0 "Pre-check Python environment & dependencies"

# Gunakan PYTHON yang pasti (fallback: cukup `python3`)
PYTHON=""
for try_py in \
    "$PROJ/.venv/bin/python3" \
    "/home/ikanx101/aurogen-0.2.0-linux-x64/runtime/python/bin/python3" \
    "/usr/bin/python3" \
    "$(command -v python3 2>/dev/null || true)"; do
    if [ -x "$try_py" ]; then
        PYTHON="$try_py"
        break
    fi
done
[ -z "$PYTHON" ] && log_fail "Python3 tidak ditemukan di sistem."

echo "  Using: $PYTHON ($($PYTHON --version 2>&1))"
PIP="$(dirname "$PYTHON")/pip3"
[ ! -x "$PIP" ] && PIP="pip3"

# Cek satu-satu, install otomatis kalau kurang
DEPS=(
    "sklearn:scikit-learn"
    "lightgbm:lightgbm"
    "xgboost:xgboost"
    "numpy:numpy"
    "pandas:pandas"
    "requests:requests"
)
MISSING=()
for dep in "${DEPS[@]}"; do
    MOD="${dep%%:*}"
    PKG="${dep##*:}"
    if ! "$PYTHON" -c "import $MOD" 2>/dev/null; then
        MISSING+=("$PKG")
    fi
done

if [ ${#MISSING[@]} -gt 0 ]; then
    echo -e "${YLW}  ⚠ Module berikut belum terinstall: ${MISSING[*]}${NC}"
    echo -e "${YLW}  → Menginstall otomatis...${NC}"
    for pkg in "${MISSING[@]}"; do
        echo "    Installing $pkg..."
        if "$PIP" install "$pkg" 2>&1 | tail -1; then
            log_ok "  $pkg terinstall"
        else
            log_fail "Gagal install $pkg. Coba: pip3 install $pkg"
        fi
    done
    # Verifikasi ulang
    for dep in "${DEPS[@]}"; do
        MOD="${dep%%:*}"
        PKG="${dep##*:}"
        "$PYTHON" -c "import $MOD" 2>/dev/null || log_fail "$PKG masih gagal di-import setelah install."
    done
    echo -e "${GRN}  ✅ Semua dependencies berhasil diinstall${NC}"
fi

# Tampilkan versi
"$PYTHON" -c "
import sklearn, lightgbm, xgboost, numpy, pandas
print(f'  scikit-learn {sklearn.__version__} | lightgbm {lightgbm.__version__} | xgboost {xgboost.__version__}')
print(f'  numpy {numpy.__version__} | pandas {pandas.__version__}')
" && log_ok "Python dependencies OK"

# Export PYTHON supaya dipakai di step selanjutnya
export PYTHON
echo "  PYTHON=$PYTHON"

# ── [1/4] Scrape data terbaru dari FIFA API ──────────────────────────────────
log_step 1 "Scraping data terbaru dari FIFA API"
cd "$PROJ"
if "$PYTHON" scraper/data/fifa_scraper.py; then
    ROWS=$("$PYTHON" -c "import csv; print(sum(1 for _ in open('fifa_worldcup2026_stats.csv'))-1)")
    MATCHES=$((ROWS / 2))
    log_ok "fifa_worldcup2026_stats.csv — $MATCHES pertandingan, $ROWS baris"
else
    log_fail "Scraper gagal. Cek koneksi internet atau perubahan API FIFA."
fi

# ── [2/4] Generate stats & bracket data untuk visualisasi web ───────────────
log_step 2 "Menghasilkan stats_data.json + bracket_data.json untuk web"
cd "$PRED"
if "$PYTHON" generate_stats.py; then
    TEAMS=$("$PYTHON" -c "import json; d=json.load(open('../stats_data.json')); print(len(d))")
    NUM_GROUPS=$("$PYTHON" -c "import json; d=json.load(open('../bracket_data.json')); print(len(d['groups']))")
    log_ok "stats_data.json — $TEAMS tim | bracket_data.json — $NUM_GROUPS grup (competition tree kini live)"
else
    log_fail "generate_stats.py gagal."
fi

# ── update angka pertandingan & tanggal di index.html ───────────────────────
cd "$PROJ"
if "$PYTHON" update_html.py; then
    log_ok "index.html diperbarui (angka pertandingan & tanggal)"
else
    log_fail "update_html.py gagal."
fi

# ── [3/4] Training & evaluasi model ML ──────────────────────────────────────
log_step 3 "Training & evaluasi 14 model klasifikasi ML"
cd "$PRED"
"$PYTHON" model_klasifikasi.py || log_fail "model_klasifikasi.py gagal."
BEST=$("$PYTHON" -c "import json; d=json.load(open('../top_models.json')); m=d['top3'][0]; print(f\"{m['model']} — Acc={m['accuracy']*100:.2f}%\")")
log_ok "top_models.json diperbarui — model terbaik: $BEST"

# ── [4/4] Prediksi peluang per negara (hanya tim fase 16 besar) ──────────────
log_step 4 "Prediksi peluang menang — tim fase 16 besar, basis 2 match terakhir"
"$PYTHON" prediksi_tim.py || log_fail "prediksi_tim.py gagal."
TOP1=$("$PYTHON" -c "import json; d=json.load(open('../top5_predictions.json')); t=d['top5'][0]; print(f\"{t['team']} ({t['win_probability']*100:.1f}%)\")")
log_ok "top5_predictions.json diperbarui — peluang tertinggi: #1 $TOP1"

# ── Summary ──────────────────────────────────────────────────────────────────
echo ""
echo -e "${GRN}══════════════════════════════════════════════════${NC}"
echo -e "${GRN}  Pipeline selesai! Semua data website diperbarui.${NC}"
echo -e "${GRN}══════════════════════════════════════════════════${NC}"
echo ""
echo "  Output files:"
echo "    fifa_worldcup2026_stats.csv   ← data mentah pertandingan"
echo "    stats_data.json               ← data statistik per tim"
echo "    bracket_data.json             ← competition tree (grup + fase gugur)"
echo "    top_models.json               ← panel perbandingan model ML"
echo "    top5_predictions.json         ← panel prediksi 5 besar (tim fase 16 besar)"
echo ""
echo "  Buka website untuk melihat pembaruan."
echo ""

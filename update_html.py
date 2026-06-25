"""
Update angka pertandingan dan tanggal di index.html berdasarkan site_meta.json.
Dipanggil oleh update.sh setelah generate_stats.py selesai.
"""

import json
import re
import sys

with open("site_meta.json", encoding="utf-8") as f:
    meta = json.load(f)

count = meta["match_count"]
date  = meta["last_match_date"]

with open("index.html", encoding="utf-8") as f:
    html = f.read()

original = html

# 1. Hero: "<strong>N pertandingan fase grup sudah selesai</strong>"
html = re.sub(
    r'<strong>(\d+) pertandingan fase grup sudah selesai</strong>',
    f'<strong>{count} pertandingan fase grup sudah selesai</strong>',
    html
)

# 2. Live tag: "Data Live · N Pertandingan"
html = re.sub(
    r'Data Live · \d+ Pertandingan',
    f'Data Live · {count} Pertandingan',
    html
)

# 3. Stat card pertandingan selesai: stat-value angka di depan label "Pertandingan Selesai"
html = re.sub(
    r'(<div class="stat-value">)\d+(</div><div class="stat-label">Pertandingan Selesai</div>)',
    f'\\g<1>{count}\\2',
    html
)

# 4. Stat card tanggal terakhir diperbarui
html = re.sub(
    r'(<div class="stat-value" style="font-size:22px;line-height:1\.3">)[^<]+(</div><div class="stat-label">Terakhir Diperbarui</div>)',
    f'\\g<1>{date}\\2',
    html
)

# 5. Section eye prediksi: "Prediksi Awal · N Pertandingan Selesai"
html = re.sub(
    r'Prediksi Awal · \d+ Pertandingan Selesai',
    f'Prediksi Awal · {count} Pertandingan Selesai',
    html
)

# 6. Chart sub: "Berdasarkan performa N pertandingan yang telah selesai."
html = re.sub(
    r'Berdasarkan performa \d+ pertandingan yang telah selesai\.',
    f'Berdasarkan performa {count} pertandingan yang telah selesai.',
    html
)

# 7. Narasi: "Dari N pertandingan yang telah selesai,"
html = re.sub(
    r'Dari \d+ pertandingan yang telah selesai,',
    f'Dari {count} pertandingan yang telah selesai,',
    html
)

if html == original:
    print(f"index.html tidak berubah (sudah {count} pertandingan, {date})")
else:
    with open("index.html", "w", encoding="utf-8") as f:
        f.write(html)
    print(f"index.html diperbarui — {count} pertandingan, terakhir {date}")

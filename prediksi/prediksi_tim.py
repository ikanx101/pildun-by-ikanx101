"""
Prediksi 5 Tim Berpeluang Menang Tertinggi
Menggunakan model terbaik (LightGBM) dengan rata-rata 3 pertandingan terakhir per tim.
Hanya tim yang telah memainkan >= 4 pertandingan yang diikutsertakan.

Cara update: jalankan ulang script ini setiap kali data CSV diperbarui.
Output: ../top5_predictions.json (dibaca langsung oleh website)
"""

import pandas as pd
import numpy as np
import json
import warnings
warnings.filterwarnings("ignore")
from datetime import date
from lightgbm import LGBMClassifier

# ── 1. Load & prep data ───────────────────────────────────────────────────────
df = pd.read_csv("../fifa_worldcup2026_stats.csv")

leaky_cols = [
    "match_id", "date", "stage", "group", "venue", "city",
    "home_team", "away_team", "team", "opponent",
    "team_goals", "opponent_goals",
    "Goals", "GoalsConceded", "GoalsConcededFromAttemptAtGoalAgainst",
    "GoalsFromDirectFreeKicks", "GoalsInsideThePenaltyArea", "GoalsOutsideThePenaltyArea",
    "OwnGoals", "PenaltiesScored",
    "CleanSheets", "MatchesPlayed",
]

drop_cols   = [c for c in leaky_cols if c in df.columns]
feature_cols = [c for c in df.columns if c not in drop_cols + ["result"]]

X = df[feature_cols].fillna(0)
y = (df["result"] == "win").astype(int)

# ── 2. Latih LightGBM pada seluruh data ──────────────────────────────────────
model = LGBMClassifier(n_estimators=100, random_state=42, verbose=-1)
model.fit(X, y)
print(f"Model dilatih  : {len(X)} baris, {len(feature_cols)} fitur")
print(f"Distribusi label: win={y.sum()}, not win={(y==0).sum()}")

# ── 3. Rata-rata 3 pertandingan terakhir per tim (hanya tim >= 4 main) ────────
df["date"] = pd.to_datetime(df["date"])

team_info = df.groupby("team").agg(
    group=("group", "first"),
    matches_played=("team_goals", "count"),
    last_stage=("stage", "last"),
).reset_index()

# Filter hanya tim dengan >= 4 pertandingan
eligible_teams = team_info[team_info["matches_played"] >= 4]["team"].tolist()
df_eligible = df[df["team"].isin(eligible_teams)]

print(f"Tim memenuhi syarat (>= 4 main): {len(eligible_teams)}")

# Ambil 3 pertandingan terakhir (berdasarkan tanggal) per tim
df_last3 = (
    df_eligible.sort_values("date")
    .groupby("team")
    .tail(3)
)

team_avg = df_last3.groupby("team")[feature_cols].mean().fillna(0)

# ── 4. Prediksi probabilitas menang ──────────────────────────────────────────
proba = model.predict_proba(team_avg)[:, 1]   # P(win)

result_df = (
    pd.DataFrame({"team": team_avg.index.tolist(), "win_probability": proba})
    .merge(team_info[team_info["team"].isin(eligible_teams)], on="team")
    .sort_values("win_probability", ascending=False)
    .reset_index(drop=True)
)
result_df["rank"] = result_df.index + 1

# ── 5. Tampilkan hasil ────────────────────────────────────────────────────────
print(f"\n{'Rank':<5} {'Tim':<28} {'Grup':<10} {'Main':<6} {'P(win)':>8}")
print("-" * 62)
for _, row in result_df.iterrows():
    marker = " ◀" if row["rank"] <= 5 else ""
    print(f"  {int(row['rank']):<4} {row['team']:<28} {row['group']:<10} "
          f"{int(row['matches_played']):<6} {row['win_probability']:.2%}{marker}")

# ── 6. Export JSON ────────────────────────────────────────────────────────────
top5 = result_df.head(5)

payload = {
    "updated_at":        str(date.today()),
    "model_used":        "LightGBM",
    "basis_prediksi":    "rata-rata 3 pertandingan terakhir, min 4 pertandingan",
    "n_teams_evaluated": len(result_df),
    "top5": [
        {
            "rank":            int(row["rank"]),
            "team":            row["team"],
            "group":           row["group"],
            "last_stage":      row.get("last_stage", ""),
            "matches_played":  int(row["matches_played"]),
            "win_probability": round(float(row["win_probability"]), 4),
        }
        for _, row in top5.iterrows()
    ],
}

with open("../top5_predictions.json", "w", encoding="utf-8") as f:
    json.dump(payload, f, indent=2, ensure_ascii=False)

print(f"\nDisimpan ke ../top5_predictions.json")

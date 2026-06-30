"""
Prediksi 5 Tim Berpeluang Menang Tertinggi — Fase Gugur
Hanya tim yang lolos ke fase gugur (32 tim) yang dievaluasi.
Basis prediksi: rata-rata 2 pertandingan terakhir per tim.

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
df["date"] = pd.to_datetime(df["date"])

leaky_cols = [
    "match_id", "date", "stage", "group", "venue", "city",
    "home_team", "away_team", "team", "opponent",
    "team_goals", "opponent_goals",
    "Goals", "GoalsConceded", "GoalsConcededFromAttemptAtGoalAgainst",
    "GoalsFromDirectFreeKicks", "GoalsInsideThePenaltyArea", "GoalsOutsideThePenaltyArea",
    "OwnGoals", "PenaltiesScored",
    "CleanSheets", "MatchesPlayed",
]

drop_cols    = [c for c in leaky_cols if c in df.columns]
feature_cols = [c for c in df.columns if c not in drop_cols + ["result"]]

X = df[feature_cols].fillna(0)
y = (df["result"] == "win").astype(int)

# ── 2. Latih LightGBM pada seluruh data ──────────────────────────────────────
model = LGBMClassifier(n_estimators=100, random_state=42, verbose=-1)
model.fit(X, y)
print(f"Model dilatih  : {len(X)} baris, {len(feature_cols)} fitur")
print(f"Distribusi label: win={y.sum()}, not win={(y==0).sum()}")

# ── 3. Tentukan tim yang masuk fase gugur ─────────────────────────────────────
group_df = df[df["stage"] == "First Stage"].copy()

# Hitung klasemen per grup (First Stage saja)
groups = {}
for grp_name in sorted(group_df["group"].dropna().unique()):
    if not grp_name:
        continue
    grp_rows = group_df[group_df["group"] == grp_name]
    teams_info = {}
    for team_name, team_rows in grp_rows.groupby("team"):
        gf  = int(team_rows["team_goals"].sum())
        ga  = int(team_rows["opponent_goals"].sum())
        w   = int((team_rows["team_goals"] > team_rows["opponent_goals"]).sum())
        d   = int((team_rows["team_goals"] == team_rows["opponent_goals"]).sum())
        pts = 3 * w + d
        teams_info[team_name] = {
            "pts": pts, "gd": gf - ga, "gf": gf, "group": grp_name
        }
    sorted_teams = sorted(
        teams_info.items(),
        key=lambda x: (-x[1]["pts"], -x[1]["gd"], -x[1]["gf"], x[0])
    )
    groups[grp_name] = sorted_teams

# Top 2 per grup → 24 tim
top2_teams = set()
third_candidates = []
for grp_name, sorted_teams in groups.items():
    top2_teams.add(sorted_teams[0][0])
    top2_teams.add(sorted_teams[1][0])
    if len(sorted_teams) >= 3:
        t = sorted_teams[2]
        third_candidates.append({
            "name": t[0],
            "pts": t[1]["pts"], "gd": t[1]["gd"], "gf": t[1]["gf"],
            "group": t[1]["group"]
        })

# 8 tim terbaik peringkat 3 → total 32 tim
third_candidates.sort(key=lambda x: (-x["pts"], -x["gd"], -x["gf"], x["name"]))
top8_third = set(t["name"] for t in third_candidates[:8])

knockout_teams = top2_teams | top8_third
print(f"\nTim lolos fase gugur: {len(knockout_teams)} tim")
print(f"  Top-2 per grup: {len(top2_teams)} tim")
print(f"  3rd terbaik   : {', '.join(sorted(top8_third))}")

# ── 4. Ambil rata-rata 2 pertandingan terakhir per tim fase gugur ─────────────
df_ko = df[df["team"].isin(knockout_teams)].copy()

df_last2 = (
    df_ko.sort_values("date")
    .groupby("team")
    .tail(2)
)

team_avg = df_last2.groupby("team")[feature_cols].mean().fillna(0)

# Metadata per tim
team_meta = df.groupby("team").agg(
    group=("group", "first"),
    matches_played=("team_goals", "count"),
    last_stage=("stage", "last"),
).reset_index()

# ── 5. Prediksi probabilitas menang ──────────────────────────────────────────
proba = model.predict_proba(team_avg)[:, 1]

result_df = (
    pd.DataFrame({"team": team_avg.index.tolist(), "win_probability": proba})
    .merge(team_meta[team_meta["team"].isin(knockout_teams)], on="team")
    .sort_values("win_probability", ascending=False)
    .reset_index(drop=True)
)
result_df["rank"] = result_df.index + 1

# ── 6. Tampilkan hasil ────────────────────────────────────────────────────────
print(f"\n{'Rank':<5} {'Tim':<28} {'Grup':<10} {'Main':<6} {'P(win)':>8}")
print("-" * 62)
for _, row in result_df.iterrows():
    marker = " ◀" if row["rank"] <= 5 else ""
    print(f"  {int(row['rank']):<4} {row['team']:<28} {row['group']:<10} "
          f"{int(row['matches_played']):<6} {row['win_probability']:.2%}{marker}")

# ── 7. Export JSON ────────────────────────────────────────────────────────────
top5 = result_df.head(5)

payload = {
    "updated_at":        str(date.today()),
    "model_used":        "LightGBM",
    "basis_prediksi":    "rata-rata 2 pertandingan terakhir, hanya tim fase gugur (32 tim)",
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

print(f"\nDisimpan ke ../top5_predictions.json ({len(result_df)} tim fase gugur dievaluasi)")

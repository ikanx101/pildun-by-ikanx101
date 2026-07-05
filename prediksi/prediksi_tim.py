"""
Prediksi 5 Tim Berpeluang Menang Tertinggi — Fase 16 Besar
Hanya tim yang lolos ke fase 16 besar (16 tim) yang dievaluasi.
Basis prediksi: rata-rata 2 pertandingan terakhir per tim.
Model yang digunakan: model dengan akurasi CV terbaik (dari top_models.json).

Cara update: jalankan ulang script ini setiap kali data CSV diperbarui.
Output: ../top5_predictions.json (dibaca langsung oleh website)
"""

import pandas as pd
import numpy as np
import json
import warnings
warnings.filterwarnings("ignore")
from datetime import date

from sklearn.preprocessing import StandardScaler
from sklearn.pipeline import Pipeline
from sklearn.linear_model import LogisticRegression
from sklearn.tree import DecisionTreeClassifier
from sklearn.ensemble import (
    RandomForestClassifier, GradientBoostingClassifier,
    ExtraTreesClassifier, AdaBoostClassifier, BaggingClassifier
)
from sklearn.svm import SVC
from sklearn.neighbors import KNeighborsClassifier
from sklearn.naive_bayes import GaussianNB
from sklearn.discriminant_analysis import LinearDiscriminantAnalysis
from xgboost import XGBClassifier
from lightgbm import LGBMClassifier

# ── 0. Tentukan model terbaik dari top_models.json ────────────────────────────
MODEL_REGISTRY = {
    "Logistic Regression":          (LogisticRegression(max_iter=1000, random_state=42), True),
    "Linear Discriminant Analysis": (LinearDiscriminantAnalysis(solver="eigen", shrinkage="auto"), True),
    "Naive Bayes":                  (GaussianNB(), False),
    "K-Nearest Neighbors":          (KNeighborsClassifier(n_neighbors=5), True),
    "Decision Tree":                (DecisionTreeClassifier(random_state=42), False),
    "Bagging":                      (BaggingClassifier(random_state=42), False),
    "Random Forest":                (RandomForestClassifier(n_estimators=200, random_state=42), False),
    "Extra Trees":                  (ExtraTreesClassifier(n_estimators=200, random_state=42), False),
    "AdaBoost":                     (AdaBoostClassifier(n_estimators=100, random_state=42), False),
    "Gradient Boosting":            (GradientBoostingClassifier(n_estimators=100, random_state=42), False),
    "XGBoost":                      (XGBClassifier(n_estimators=100, eval_metric="logloss",
                                                    random_state=42, verbosity=0), False),
    "LightGBM":                     (LGBMClassifier(n_estimators=100, random_state=42, verbose=-1), False),
    "SVM (RBF)":                    (SVC(kernel="rbf", probability=True, random_state=42), True),
    "SVM (Linear)":                 (SVC(kernel="linear", probability=True, random_state=42), True),
}

try:
    with open("../top_models.json", encoding="utf-8") as f:
        top_models_data = json.load(f)
    best_model_name = top_models_data["top3"][0]["model"]
    best_accuracy   = top_models_data["top3"][0]["accuracy"]
except Exception:
    best_model_name = "LightGBM"
    best_accuracy   = None

if best_model_name not in MODEL_REGISTRY:
    print(f"  ⚠ Model '{best_model_name}' tidak ada di registry, fallback ke LightGBM")
    best_model_name = "LightGBM"

base_clf, needs_scaling = MODEL_REGISTRY[best_model_name]
print(f"Model terpilih : {best_model_name}" +
      (f" (Acc CV={best_accuracy:.4f})" if best_accuracy else ""))

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

# ── 2. Latih model terbaik pada seluruh data ─────────────────────────────────
if needs_scaling:
    model = Pipeline([("scaler", StandardScaler()), ("clf", base_clf)])
else:
    model = base_clf

model.fit(X, y)
print(f"Model dilatih  : {len(X)} baris, {len(feature_cols)} fitur")
print(f"Distribusi label: win={y.sum()}, not win={(y==0).sum()}")

# ── 3. Tentukan tim yang lolos ke fase 16 besar ───────────────────────────────
# Sumber 1: pemenang Round of 32 di waktu normal (result == "win" di CSV)
r32 = df[df["stage"] == "Round of 32"]
r16_teams = set(r32.loc[r32["result"] == "win", "team"])

# Sumber 2: tim yang sudah bermain di babak 16 besar atau setelahnya pasti lolos.
# Ini menangkap pemenang lewat babak tambahan/penalti yang skornya seri di CSV.
post_r32 = df[~df["stage"].isin(["First Stage", "Round of 32"])]
r16_teams |= set(post_r32["team"])

# Sumber 3: field "winner" di bracket_data.json (termasuk pemenang adu penalti
# yang laganya belum tercatat di babak berikutnya)
try:
    with open("../bracket_data.json", encoding="utf-8") as f:
        bracket = json.load(f)
    for m in bracket.get("rounds", {}).get("R32", []):
        if m.get("winner"):
            r16_teams.add(m["winner"])
    for rnd in ("R16", "QF", "SF", "Final"):
        for m in bracket.get("rounds", {}).get(rnd, []):
            for side in ("home", "away"):
                if m.get(side):
                    r16_teams.add(m[side])
except Exception as e:
    print(f"  ⚠ bracket_data.json tidak terbaca ({e}), pakai data CSV saja")

# Sumber 4: override manual — pemenang adu penalti yang belum terekam di
# CSV maupun bracket_data.json. Hapus entri jika data scraper sudah lengkap.
MANUAL_QUALIFIERS = {
    "Egypt",  # menang adu penalti vs Australia (R32, 3 Juli 2026)
}
r16_teams |= MANUAL_QUALIFIERS

# Laga R32 yang pemenangnya belum bisa ditentukan dari sumber di atas
unresolved = []
for _, m in r32.drop_duplicates("match_id").iterrows():
    if m["team"] not in r16_teams and m["opponent"] not in r16_teams:
        unresolved.append(f"{m['team']} vs {m['opponent']}")

print(f"\nTim lolos fase 16 besar: {len(r16_teams)} tim")
print(f"  {', '.join(sorted(r16_teams))}")
if unresolved:
    print(f"  ⚠ Pemenang belum diketahui (seri, hasil penalti belum tersedia): "
          f"{'; '.join(unresolved)}")
if len(r16_teams) != 16:
    print(f"  ⚠ Jumlah tim ≠ 16 — data babak 32 besar kemungkinan belum lengkap")

# ── 4. Ambil rata-rata 2 pertandingan terakhir per tim 16 besar ───────────────
df_ko = df[df["team"].isin(r16_teams)].copy()

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
    .merge(team_meta[team_meta["team"].isin(r16_teams)], on="team")
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
    "model_used":        best_model_name,
    "model_accuracy":    best_accuracy,
    "basis_prediksi":    "rata-rata 2 pertandingan terakhir, hanya tim fase 16 besar",
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

print(f"\nDisimpan ke ../top5_predictions.json ({len(result_df)} tim fase 16 besar dievaluasi)")

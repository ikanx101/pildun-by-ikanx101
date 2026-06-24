"""
Klasifikasi Hasil Pertandingan FIFA World Cup 2026
Target: prediksi apakah tim "menang" atau "tidak menang"
"""

import pandas as pd
import numpy as np
import warnings
warnings.filterwarnings("ignore")

from sklearn.model_selection import StratifiedKFold, cross_val_score
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
from sklearn.discriminant_analysis import LinearDiscriminantAnalysis, QuadraticDiscriminantAnalysis
from xgboost import XGBClassifier
from lightgbm import LGBMClassifier

# ── 1. Load data ──────────────────────────────────────────────────────────────
df = pd.read_csv("../fifa_worldcup2026_stats.csv")
print(f"Total baris: {len(df)}")
print(f"Distribusi label:\n{df['result'].value_counts()}\n")

# ── 2. Hapus fitur yang bocor langsung ke label ───────────────────────────────
# Fitur ini LANGSUNG menentukan menang/kalah → harus dibuang agar model adil
leaky_cols = [
    "match_id", "date", "stage", "group", "venue", "city",
    "home_team", "away_team", "team", "opponent",
    # gol langsung bocor
    "team_goals", "opponent_goals",
    "Goals", "GoalsConceded", "GoalsConcededFromAttemptAtGoalAgainst",
    "GoalsFromDirectFreeKicks", "GoalsInsideThePenaltyArea", "GoalsOutsideThePenaltyArea",
    "OwnGoals", "PenaltiesScored",
    "CleanSheets",       # 1 jika tidak kebobolan → leaky
    "MatchesPlayed",     # selalu 1, tidak informatif
]

drop_cols = [c for c in leaky_cols if c in df.columns]
feature_cols = [c for c in df.columns if c not in drop_cols + ["result"]]

X = df[feature_cols].fillna(0)
y = (df["result"] == "win").astype(int)   # 1 = menang, 0 = tidak menang

print(f"Jumlah fitur yang digunakan: {len(feature_cols)}")
print(f"Kelas: 1=menang ({y.sum()}), 0=tidak menang ({(y==0).sum()})\n")

# ── 3. Definisi model ─────────────────────────────────────────────────────────
models = {
    "Logistic Regression":        LogisticRegression(max_iter=1000, random_state=42),
    "Linear Discriminant Analysis": LinearDiscriminantAnalysis(solver="eigen", shrinkage="auto"),
    "Naive Bayes":                GaussianNB(),
    "K-Nearest Neighbors":        KNeighborsClassifier(n_neighbors=5),
    "Decision Tree":              DecisionTreeClassifier(random_state=42),
    "Bagging":                    BaggingClassifier(random_state=42),
    "Random Forest":              RandomForestClassifier(n_estimators=200, random_state=42),
    "Extra Trees":                ExtraTreesClassifier(n_estimators=200, random_state=42),
    "AdaBoost":                   AdaBoostClassifier(n_estimators=100, random_state=42),
    "Gradient Boosting":          GradientBoostingClassifier(n_estimators=100, random_state=42),
    "XGBoost":                    XGBClassifier(n_estimators=100, eval_metric="logloss",
                                                random_state=42, verbosity=0),
    "LightGBM":                   LGBMClassifier(n_estimators=100, random_state=42, verbose=-1),
    "SVM (RBF)":                  SVC(kernel="rbf", probability=True, random_state=42),
    "SVM (Linear)":               SVC(kernel="linear", probability=True, random_state=42),
}

# Model yang butuh scaling fitur
needs_scaling = {
    "Logistic Regression", "K-Nearest Neighbors",
    "SVM (RBF)", "SVM (Linear)",
    "Linear Discriminant Analysis",
}

# ── 4. Evaluasi cross-validation (StratifiedKFold, k=10) ─────────────────────
cv = StratifiedKFold(n_splits=10, shuffle=True, random_state=42)
metrics = ["accuracy", "f1", "roc_auc"]

results = []

for name, model in models.items():
    if name in needs_scaling:
        pipe = Pipeline([("scaler", StandardScaler()), ("clf", model)])
    else:
        pipe = model

    row = {"Model": name}
    for metric in metrics:
        scores = cross_val_score(pipe, X, y, cv=cv, scoring=metric)
        row[f"{metric}_mean"] = scores.mean()
        row[f"{metric}_std"]  = scores.std()

    results.append(row)
    print(f"  {name:35s} | Acc={row['accuracy_mean']:.4f} ± {row['accuracy_std']:.4f}"
          f" | F1={row['f1_mean']:.4f} | AUC={row['roc_auc_mean']:.4f}")

# ── 5. Tabel perbandingan ─────────────────────────────────────────────────────
results_df = pd.DataFrame(results).sort_values("accuracy_mean", ascending=False).reset_index(drop=True)
results_df["Rank"] = results_df.index + 1

print("\n" + "="*85)
print("TABEL PERBANDINGAN AKURASI MODEL")
print("="*85)
print(f"{'Rank':<5} {'Model':<38} {'Accuracy':>10} {'±Std':>8} {'F1-Score':>10} {'AUC-ROC':>10}")
print("-"*85)
for _, row in results_df.iterrows():
    print(f"{int(row['Rank']):<5} {row['Model']:<38} "
          f"{row['accuracy_mean']:>9.4f} {row['accuracy_std']:>8.4f} "
          f"{row['f1_mean']:>10.4f} {row['roc_auc_mean']:>10.4f}")
print("="*85)

# ── 6. Feature Importance (Random Forest & XGBoost) ──────────────────────────
print("\n--- Top 15 Feature Importance (Random Forest) ---")
rf = RandomForestClassifier(n_estimators=200, random_state=42)
rf.fit(X, y)
fi_rf = pd.Series(rf.feature_importances_, index=feature_cols).sort_values(ascending=False).head(15)
for feat, imp in fi_rf.items():
    print(f"  {feat:<45} {imp:.4f}")

print("\n--- Top 15 Feature Importance (XGBoost) ---")
xgb = XGBClassifier(n_estimators=100, eval_metric="logloss", random_state=42, verbosity=0)
xgb.fit(X, y)
fi_xgb = pd.Series(xgb.feature_importances_, index=feature_cols).sort_values(ascending=False).head(15)
for feat, imp in fi_xgb.items():
    print(f"  {feat:<45} {imp:.4f}")

# ── 7. Simpan hasil ───────────────────────────────────────────────────────────
results_df.to_csv("hasil_perbandingan_model.csv", index=False)
fi_rf.reset_index().rename(columns={"index": "feature", 0: "importance"}).to_csv(
    "feature_importance_rf.csv", index=False)
fi_xgb.reset_index().rename(columns={"index": "feature", 0: "importance"}).to_csv(
    "feature_importance_xgb.csv", index=False)

# ── 8. Export top_models.json untuk website ───────────────────────────────────
import json
from datetime import date

top3_rows = results_df.head(3)
top_models_payload = {
    "updated_at": str(date.today()),
    "n_samples": len(df),
    "n_features": len(feature_cols),
    "cv_folds": 10,
    "top3": [
        {
            "rank": i + 1,
            "model": row["Model"],
            "accuracy": round(row["accuracy_mean"], 4),
            "accuracy_std": round(row["accuracy_std"], 4),
            "f1": round(row["f1_mean"], 4),
            "auc_roc": round(row["roc_auc_mean"], 4),
        }
        for i, (_, row) in enumerate(top3_rows.iterrows())
    ],
}

with open("../top_models.json", "w") as f:
    json.dump(top_models_payload, f, indent=2)

print("\nHasil disimpan ke:")
print("  - hasil_perbandingan_model.csv")
print("  - feature_importance_rf.csv")
print("  - feature_importance_xgb.csv")
print("  - ../top_models.json  ← dibaca website secara otomatis")

"""
Generate stats_data.json untuk visualisasi web utama.
Dibaca oleh index.html secara dinamis — jalankan ulang setiap kali data CSV diperbarui.
"""

import pandas as pd
import json
import sys

df = pd.read_csv("../fifa_worldcup2026_stats.csv")

print(f"Data dimuat: {len(df)} baris, {df['team'].nunique()} tim")

result = {}
for team, grp in df.groupby("team"):
    wins       = int((grp["result"] == "win").sum())
    draws      = int((grp["team_goals"] == grp["opponent_goals"]).sum())
    losses     = int(len(grp) - wins - draws)
    gf         = int(grp["team_goals"].sum())
    ga         = int(grp["opponent_goals"].sum())
    xg         = round(float(grp["XG"].sum()), 2)
    shots_avg  = round(float(grp["AttemptAtGoal"].mean()), 1)
    shots_tot  = float(grp["AttemptAtGoal"].sum())
    threat     = int(grp["Threat"].sum())
    pressing   = int(grp["DefensivePressuresApplied"].sum())
    top_spd    = round(float(grp["TopSpeed"].max()), 1)
    pts        = int(3 * wins + draws)
    gd         = gf - ga
    poss       = round(float(grp["Possession"].mean() * 100), 1)
    conv       = round(gf / shots_tot * 100, 1) if shots_tot > 0 else 0.0

    result[team] = {
        "group":          grp["group"].iloc[0],
        "matches":        len(grp),
        "wins":           wins,
        "draws":          draws,
        "losses":         losses,
        "goals_for":      gf,
        "goals_against":  ga,
        "xg":             xg,
        "shots":          shots_avg,
        "threat":         threat,
        "pressing":       pressing,
        "top_speed":      top_spd,
        "points":         pts,
        "gd":             gd,
        "possession_avg": poss,
        "conversion":     conv,
    }

with open("../stats_data.json", "w", encoding="utf-8") as f:
    json.dump(result, f, indent=2, ensure_ascii=False)

print(f"stats_data.json disimpan — {len(result)} tim")

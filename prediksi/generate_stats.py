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

# Hitung metadata untuk update index.html
total_matches = len(df) // 2
last_date = pd.to_datetime(df["date"]).max()
months_id = {
    1:"Januari",2:"Februari",3:"Maret",4:"April",5:"Mei",6:"Juni",
    7:"Juli",8:"Agustus",9:"September",10:"Oktober",11:"November",12:"Desember"
}
last_date_id = f"{last_date.day} {months_id[last_date.month]} {last_date.year}"

site_meta = {"match_count": total_matches, "last_match_date": last_date_id}
with open("../site_meta.json", "w", encoding="utf-8") as f:
    json.dump(site_meta, f, indent=2, ensure_ascii=False)

print(f"site_meta.json disimpan — {total_matches} pertandingan, terakhir {last_date_id}")

# ── GENERATE BRACKET DATA ─────────────────────────────────────────────────────
from collections import defaultdict

group_df = df[df["stage"] == "First Stage"].copy()

# Build group standings from First Stage only
groups_bracket = {}
for grp_name in sorted(group_df["group"].dropna().unique()):
    if not grp_name:
        continue
    grp_rows = group_df[group_df["group"] == grp_name]
    teams_info = {}
    for team_name, team_rows in grp_rows.groupby("team"):
        gf = int(team_rows["team_goals"].sum())
        ga = int(team_rows["opponent_goals"].sum())
        w  = int((team_rows["team_goals"] > team_rows["opponent_goals"]).sum())
        d  = int((team_rows["team_goals"] == team_rows["opponent_goals"]).sum())
        l  = int((team_rows["team_goals"] < team_rows["opponent_goals"]).sum())
        pts = 3 * w + d
        teams_info[team_name] = {
            "name": team_name, "played": len(team_rows),
            "wins": w, "draws": d, "losses": l,
            "gf": gf, "ga": ga, "gd": gf - ga, "pts": pts
        }
    sorted_teams = sorted(
        teams_info.values(),
        key=lambda x: (-x["pts"], -x["gd"], -x["gf"], x["name"])
    )
    for i, t in enumerate(sorted_teams):
        t["pos"] = i + 1
    complete = all(t["played"] >= 3 for t in sorted_teams)
    groups_bracket[grp_name] = {
        "name": grp_name,
        "complete": complete,
        "teams": sorted_teams
    }

# Determine 8 best 3rd-place teams
third_teams = []
for g, data in groups_bracket.items():
    if len(data["teams"]) >= 3:
        t = dict(data["teams"][2])
        t["from_group"] = g
        third_teams.append(t)
third_teams.sort(key=lambda x: (-x["pts"], -x["gd"], -x["gf"], x["name"]))
top8_third = [t["name"] for t in third_teams[:8]]

# Build knockout round data
def build_round(stage_name):
    r_df = df[df["stage"] == stage_name]
    if len(r_df) == 0:
        return []
    matches = {}
    for _, row in r_df.iterrows():
        key = tuple(sorted([row["home_team"], row["away_team"]]))
        if key not in matches:
            matches[key] = {
                "home": row["home_team"], "away": row["away_team"],
                "home_score": None, "away_score": None, "winner": None,
                "date": str(row["date"])
            }
        if row["team"] == row["home_team"]:
            matches[key]["home_score"] = int(row["team_goals"])
            matches[key]["away_score"] = int(row["opponent_goals"])
        if row["result"] == "win":
            matches[key]["winner"] = row["team"]
    return sorted(matches.values(), key=lambda x: x["date"])

stage_names = {
    "R32": "Round of 32",
    "R16": "Round of 16",
    "QF":  "Quarter-finals",
    "SF":  "Semi-finals",
    "Final": "Final"
}

rounds = {k: build_round(v) for k, v in stage_names.items()}

bracket_data = {
    "updated_at":      last_date_id,
    "groups":          list(groups_bracket.values()),
    "third_qualifiers": top8_third,
    "rounds":          rounds
}

with open("../bracket_data.json", "w", encoding="utf-8") as f:
    json.dump(bracket_data, f, indent=2, ensure_ascii=False)

print(f"bracket_data.json disimpan — {len(bracket_data['groups'])} grup, top8_3rd: {top8_third}")

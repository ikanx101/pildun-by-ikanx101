"""
FIFA World Cup 2026 - Match Statistics Scraper
Scrapes all completed match statistics from FIFA API
Output: data/fifa_worldcup2026_stats.csv
"""

import requests
import csv
import time
import os
from datetime import datetime

HEADERS = {
    "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
}

CALENDAR_API = (
    "https://api.fifa.com/api/v3/calendar/matches"
    "?language=en&idCompetition=17&idSeason=285023&idStage=289273&count=400"
)
STATS_API = "https://fdh-api.fifa.com/v1/stats/match/{id_ifes}/teams.json"

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
OUTPUT_FILE = os.path.join(SCRIPT_DIR, "fifa_worldcup2026_stats.csv")


def get_finished_matches():
    resp = requests.get(CALENDAR_API, headers=HEADERS, timeout=30)
    resp.raise_for_status()
    matches = resp.json()["Results"]
    # MatchStatus == 0 means finished
    return [m for m in matches if m.get("MatchStatus") == 0]


def get_team_stats(id_ifes):
    url = STATS_API.format(id_ifes=id_ifes)
    resp = requests.get(url, headers=HEADERS, timeout=30)
    resp.raise_for_status()
    return resp.json()


def parse_match_info(match):
    def get_locale(items, locale="en-GB"):
        for item in (items or []):
            if item.get("Locale") == locale:
                return item.get("Description", "")
        return items[0].get("Description", "") if items else ""

    date_str = match.get("Date", "")
    date_parsed = ""
    if date_str:
        try:
            date_parsed = datetime.strptime(date_str, "%Y-%m-%dT%H:%M:%SZ").strftime("%Y-%m-%d")
        except Exception:
            date_parsed = date_str[:10]

    stage = get_locale(match.get("StageName", []))
    group = get_locale(match.get("GroupName", []))
    stadium = match.get("Stadium", {})
    venue = get_locale(stadium.get("Name", []))
    city = get_locale(stadium.get("CityName", []))

    return {
        "match_id": match["IdMatch"],
        "date": date_parsed,
        "stage": stage,
        "group": group,
        "venue": venue,
        "city": city,
    }


def build_rows(match, stats_by_team):
    """Return list of two dicts (one per team) for this match."""
    base = parse_match_info(match)

    home = match["Home"]
    away = match["Away"]

    home_id = home["IdTeam"]
    away_id = away["IdTeam"]
    home_name = home["ShortClubName"]
    away_name = away["ShortClubName"]
    home_score = match.get("HomeTeamScore", 0) or 0
    away_score = match.get("AwayTeamScore", 0) or 0

    rows = []
    for team_id, team_name, opp_name, team_score, opp_score in [
        (home_id, home_name, away_name, home_score, away_score),
        (away_id, away_name, home_name, away_score, home_score),
    ]:
        row = {**base}
        row["home_team"] = home_name
        row["away_team"] = away_name
        row["team"] = team_name
        row["opponent"] = opp_name
        row["team_goals"] = team_score
        row["opponent_goals"] = opp_score

        # Determine result
        if team_score > opp_score:
            row["result"] = "win"
        else:
            row["result"] = "not win"

        # Add all stats for this team
        team_stats = stats_by_team.get(team_id, [])
        for stat_entry in team_stats:
            stat_name = stat_entry[0]
            stat_value = stat_entry[1]
            row[stat_name] = stat_value

        rows.append(row)

    return rows


def main():
    print("Fetching finished matches...")
    matches = get_finished_matches()
    print(f"Found {len(matches)} finished match(es)")

    all_rows = []
    all_stat_keys = []

    for i, match in enumerate(matches):
        home = match["Home"]["ShortClubName"]
        away = match["Away"]["ShortClubName"]
        id_ifes = match.get("Properties", {}).get("IdIFES")

        print(f"[{i+1}/{len(matches)}] {home} vs {away} (IdIFES={id_ifes})")

        if not id_ifes:
            print("  WARNING: No IdIFES, skipping stats")
            stats_by_team = {}
        else:
            try:
                raw_stats = get_team_stats(id_ifes)
                # raw_stats keys are team IDs (as strings)
                stats_by_team = raw_stats
                # Collect stat names for CSV header (from first team)
                for team_id, stat_list in raw_stats.items():
                    if not all_stat_keys and stat_list:
                        all_stat_keys = [s[0] for s in stat_list]
                    break
            except Exception as e:
                print(f"  ERROR fetching stats: {e}")
                stats_by_team = {}

        rows = build_rows(match, stats_by_team)
        all_rows.extend(rows)
        time.sleep(0.3)

    if not all_rows:
        print("No data to write.")
        return

    # Build header: match fields + team fields + all stats
    match_fields = ["match_id", "date", "stage", "group", "venue", "city",
                    "home_team", "away_team", "team", "opponent",
                    "team_goals", "opponent_goals"]
    fieldnames = match_fields + all_stat_keys + ["result"]

    print(f"\nWriting {len(all_rows)} rows to {OUTPUT_FILE}...")
    with open(OUTPUT_FILE, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(all_rows)

    print(f"Done! Saved to {OUTPUT_FILE}")
    print(f"Columns: {len(fieldnames)}, Rows: {len(all_rows)}")


if __name__ == "__main__":
    main()

from flask import Flask, render_template, request, jsonify, send_file
import json
import os
import csv
import io
import unicodedata
import requests
from datetime import datetime, timedelta

app = Flask(__name__)

# ========================================
# Data Storage (use environment variable for persistence path)
# ========================================
DATA_DIR = os.environ.get('DATA_DIR', '.')
ENTRIES_FILE = os.path.join(DATA_DIR, "entries.json")

# ========================================
# NFL Team mappings
# ========================================
NFL_TEAMS = {
    "ARI": "Arizona Cardinals", "ATL": "Atlanta Falcons", "BAL": "Baltimore Ravens",
    "BUF": "Buffalo Bills", "CAR": "Carolina Panthers", "CHI": "Chicago Bears",
    "CIN": "Cincinnati Bengals", "CLE": "Cleveland Browns", "DAL": "Dallas Cowboys",
    "DEN": "Denver Broncos", "DET": "Detroit Lions", "GB": "Green Bay Packers",
    "HOU": "Houston Texans", "IND": "Indianapolis Colts", "JAX": "Jacksonville Jaguars",
    "KC": "Kansas City Chiefs", "LV": "Las Vegas Raiders", "LAC": "Los Angeles Chargers",
    "LAR": "Los Angeles Rams", "MIA": "Miami Dolphins", "MIN": "Minnesota Vikings",
    "NE": "New England Patriots", "NO": "New Orleans Saints", "NYG": "New York Giants",
    "NYJ": "New York Jets", "PHI": "Philadelphia Eagles", "PIT": "Pittsburgh Steelers",
    "SF": "San Francisco 49ers", "SEA": "Seattle Seahawks", "TB": "Tampa Bay Buccaneers",
    "TEN": "Tennessee Titans", "WAS": "Washington Commanders", "WSH": "Washington Commanders"
}

# ========================================
# NBA Team mappings
# ========================================
NBA_TEAMS = {
    "ATL": "Atlanta Hawks", "BOS": "Boston Celtics", "BKN": "Brooklyn Nets",
    "CHA": "Charlotte Hornets", "CHI": "Chicago Bulls", "CLE": "Cleveland Cavaliers",
    "DAL": "Dallas Mavericks", "DEN": "Denver Nuggets", "DET": "Detroit Pistons",
    "GS": "Golden State Warriors", "GSW": "Golden State Warriors",
    "HOU": "Houston Rockets", "IND": "Indiana Pacers",
    "LAC": "Los Angeles Clippers", "LA": "Los Angeles Clippers",
    "LAL": "Los Angeles Lakers", "MEM": "Memphis Grizzlies",
    "MIA": "Miami Heat", "MIL": "Milwaukee Bucks", "MIN": "Minnesota Timberwolves",
    "NO": "New Orleans Pelicans", "NOP": "New Orleans Pelicans",
    "NY": "New York Knicks", "NYK": "New York Knicks",
    "OKC": "Oklahoma City Thunder", "ORL": "Orlando Magic",
    "PHI": "Philadelphia 76ers", "PHX": "Phoenix Suns", "POR": "Portland Trail Blazers",
    "SAC": "Sacramento Kings", "SA": "San Antonio Spurs", "SAS": "San Antonio Spurs",
    "TOR": "Toronto Raptors", "UTA": "Utah Jazz", "UTAH": "Utah Jazz",
    "WAS": "Washington Wizards", "WSH": "Washington Wizards"
}

# ========================================
# Helper functions
# ========================================
def load_json(filepath):
    if os.path.exists(filepath):
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                return json.load(f)
        except:
            return []
    return []

def save_json(filepath, data):
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)

def normalize_name(text):
    """Remove accents and normalize text for comparison."""
    normalized = unicodedata.normalize('NFD', text)
    ascii_text = ''.join(c for c in normalized if unicodedata.category(c) != 'Mn')
    return ascii_text.lower()

# ========================================
# NBA API Functions (using ESPN)
# ========================================
def get_nba_player_info(player_name: str):
    """Look up an NBA player using ESPN API."""
    try:
        search_normalized = normalize_name(player_name)
        headers = {"User-Agent": "Mozilla/5.0"}
        
        search_url = f"https://site.api.espn.com/apis/common/v3/search?query={player_name}&limit=10&type=player&sport=basketball&league=nba"
        response = requests.get(search_url, headers=headers, timeout=10)
        
        if response.status_code != 200:
            return {"error": "Failed to search for player"}
        
        data = response.json()
        nba_players = data.get("items", [])
        
        if not nba_players:
            return {"error": f"No NBA player found matching '{player_name}'"}
        
        if len(nba_players) > 1:
            exact_match = None
            for p in nba_players:
                if normalize_name(p.get("displayName", "")) == search_normalized:
                    exact_match = p
                    break
            
            if exact_match:
                nba_players = [exact_match]
            else:
                player_list = []
                for p in nba_players[:5]:
                    team_rels = p.get("teamRelationships", [])
                    team_abbr = team_rels[0].get("core", {}).get("abbreviation", "?") if team_rels else "?"
                    player_list.append({"name": p.get("displayName"), "team": team_abbr})
                return {"multiple": player_list}
        
        player = nba_players[0]
        player_full_name = player.get("displayName", "Unknown")
        
        team_rels = player.get("teamRelationships", [])
        if team_rels:
            team_core = team_rels[0].get("core", {})
            team_abbr = team_core.get("abbreviation", "")
            team_name = team_core.get("displayName", NBA_TEAMS.get(team_abbr, "Unknown"))
            team_id = team_core.get("id", "")
        else:
            team_abbr = ""
            team_name = "Unknown"
            team_id = ""
        
        next_opponent = None
        game_date = None
        
        if team_id:
            schedule_url = f"https://site.api.espn.com/apis/site/v2/sports/basketball/nba/teams/{team_id}/schedule"
            sched_response = requests.get(schedule_url, headers=headers, timeout=10)
            
            if sched_response.status_code == 200:
                sched_data = sched_response.json()
                events = sched_data.get("events", [])
                
                now = datetime.now()
                if now.hour >= 22:
                    now = now + timedelta(days=1)
                
                for event in events:
                    event_date_str = event.get("date", "")
                    if event_date_str:
                        try:
                            event_date = datetime.fromisoformat(event_date_str.replace("Z", "+00:00"))
                            if event_date.date() >= now.date():
                                competitions = event.get("competitions", [])
                                if competitions:
                                    competitors = competitions[0].get("competitors", [])
                                    for comp in competitors:
                                        comp_abbr = comp.get("team", {}).get("abbreviation", "")
                                        if comp_abbr != team_abbr:
                                            next_opponent = NBA_TEAMS.get(comp_abbr, comp.get("team", {}).get("displayName", "Unknown"))
                                            game_date = event_date.strftime("%Y-%m-%d")
                                            break
                                break
                        except:
                            continue
        
        return {
            "player": player_full_name,
            "team": team_name,
            "team_abbr": team_abbr,
            "next_opponent": next_opponent,
            "game_date": game_date,
            "league": "NBA",
            "position": "NBA Player"
        }
        
    except Exception as e:
        return {"error": str(e)}

# ========================================
# NFL API Functions (using ESPN)
# ========================================
def get_nfl_player_info(player_name: str):
    """Look up an NFL player using ESPN API."""
    try:
        search_normalized = normalize_name(player_name)
        headers = {"User-Agent": "Mozilla/5.0"}
        
        search_url = f"https://site.api.espn.com/apis/common/v3/search?query={player_name}&limit=10&type=player&sport=football&league=nfl"
        response = requests.get(search_url, headers=headers, timeout=10)
        
        if response.status_code != 200:
            return {"error": "Failed to search for player"}
        
        data = response.json()
        nfl_players = data.get("items", [])
        
        if not nfl_players:
            return {"error": f"No NFL player found matching '{player_name}'"}
        
        if len(nfl_players) > 1:
            exact_match = None
            for p in nfl_players:
                if normalize_name(p.get("displayName", "")) == search_normalized:
                    exact_match = p
                    break
            
            if exact_match:
                nfl_players = [exact_match]
            else:
                player_list = []
                for p in nfl_players[:5]:
                    team_rels = p.get("teamRelationships", [])
                    team_abbr = team_rels[0].get("core", {}).get("abbreviation", "?") if team_rels else "?"
                    player_list.append({"name": p.get("displayName"), "team": team_abbr})
                return {"multiple": player_list}
        
        player = nfl_players[0]
        player_full_name = player.get("displayName", "Unknown")
        player_id = player.get("id", "")
        
        team_rels = player.get("teamRelationships", [])
        if team_rels:
            team_core = team_rels[0].get("core", {})
            team_abbr = team_core.get("abbreviation", "")
            team_name = team_core.get("displayName", NFL_TEAMS.get(team_abbr, "Unknown"))
            team_id = team_core.get("id", "")
        else:
            team_abbr = ""
            team_name = "Unknown"
            team_id = ""
        
        position = None
        position_abbr = None
        if player_id:
            try:
                athlete_url = f"https://sports.core.api.espn.com/v2/sports/football/leagues/nfl/athletes/{player_id}"
                athlete_response = requests.get(athlete_url, headers=headers, timeout=10)
                
                if athlete_response.status_code == 200:
                    athlete_data = athlete_response.json()
                    if "position" in athlete_data:
                        position_info = athlete_data["position"]
                        position = position_info.get("name", "")
                        position_abbr = position_info.get("abbreviation", "")
            except:
                pass
        
        position_map = {
            "QB": "Quarterback (QB)",
            "RB": "Running Back (RB)",
            "FB": "Running Back (RB)",
            "WR": "Wide Receiver (WR)",
            "TE": "Wide Receiver (WR)",
            "K": "Kicker (K)",
            "P": "Kicker (K)",
            "LB": "NFL Defense Player",
            "DE": "NFL Defense Player",
            "DT": "NFL Defense Player",
            "CB": "NFL Defense Player",
            "S": "NFL Defense Player",
            "SS": "NFL Defense Player",
            "FS": "NFL Defense Player",
            "OLB": "NFL Defense Player",
            "ILB": "NFL Defense Player",
            "MLB": "NFL Defense Player",
            "NT": "NFL Defense Player",
            "DB": "NFL Defense Player",
            "DL": "NFL Defense Player",
            "EDGE": "NFL Defense Player",
        }
        form_position = position_map.get(position_abbr, "Quarterback (QB)")
        
        next_opponent = None
        game_date = None
        
        if team_id:
            schedule_url = f"https://site.api.espn.com/apis/site/v2/sports/football/nfl/teams/{team_id}/schedule"
            sched_response = requests.get(schedule_url, headers=headers, timeout=10)
            
            if sched_response.status_code == 200:
                sched_data = sched_response.json()
                events = sched_data.get("events", [])
                
                now = datetime.now()
                if now.hour >= 22:
                    now = now + timedelta(days=1)
                
                for event in events:
                    event_date_str = event.get("date", "")
                    if event_date_str:
                        try:
                            event_date = datetime.fromisoformat(event_date_str.replace("Z", "+00:00"))
                            if event_date.date() >= now.date():
                                competitions = event.get("competitions", [])
                                if competitions:
                                    competitors = competitions[0].get("competitors", [])
                                    for comp in competitors:
                                        comp_abbr = comp.get("team", {}).get("abbreviation", "")
                                        if comp_abbr != team_abbr:
                                            next_opponent = NFL_TEAMS.get(comp_abbr, comp.get("team", {}).get("displayName", "Unknown"))
                                            game_date = event_date.strftime("%Y-%m-%d")
                                            break
                                break
                        except:
                            continue
        
        return {
            "player": player_full_name,
            "team": team_name,
            "team_abbr": team_abbr,
            "next_opponent": next_opponent,
            "game_date": game_date,
            "league": "NFL",
            "position": form_position,
            "position_abbr": position_abbr
        }
        
    except Exception as e:
        return {"error": str(e)}

# ========================================
# Routes
# ========================================
@app.route("/")
def index():
    return render_template("index.html")

@app.route("/api/lookup-player", methods=["POST"])
def lookup_player():
    data = request.json
    player_name = data.get("player_name", "").strip()
    league = data.get("league", "auto")
    
    if not player_name:
        return jsonify({"error": "No player name provided"})
    
    if league == "nfl":
        result = get_nfl_player_info(player_name)
        return jsonify(result)
    elif league == "nba":
        result = get_nba_player_info(player_name)
        return jsonify(result)
    else:
        nfl_result = get_nfl_player_info(player_name)
        if not nfl_result.get("error"):
            return jsonify(nfl_result)
        
        nba_result = get_nba_player_info(player_name)
        if not nba_result.get("error"):
            return jsonify(nba_result)
        
        return jsonify({"error": f"No player found matching '{player_name}' in NFL or NBA"})

@app.route("/api/entries", methods=["GET"])
def get_entries():
    entries = load_json(ENTRIES_FILE)
    return jsonify(entries)

@app.route("/api/entries", methods=["POST"])
def add_entry():
    data = request.json
    entries = load_json(ENTRIES_FILE)
    
    entry_id = data.get("id")
    if entry_id is not None and 0 <= entry_id < len(entries):
        entries[entry_id] = data
    else:
        data["id"] = len(entries)
        entries.append(data)
    
    save_json(ENTRIES_FILE, entries)
    return jsonify({"success": True, "entries": entries})

@app.route("/api/entries/<int:entry_id>", methods=["DELETE"])
def delete_entry(entry_id):
    entries = load_json(ENTRIES_FILE)
    if 0 <= entry_id < len(entries):
        entries.pop(entry_id)
        for i, entry in enumerate(entries):
            entry["id"] = i
        save_json(ENTRIES_FILE, entries)
    return jsonify({"success": True, "entries": entries})

@app.route("/api/export-csv")
def export_csv():
    entries = load_json(ENTRIES_FILE)
    
    if not entries:
        return jsonify({"error": "No entries to export"})
    
    output = io.StringIO()
    fieldnames = ["Player", "PlayerTeam", "OppTeam", "Position", "Stat",
                  "LineMode", "LineValue", "Pick", "Level", "Multiplier"]
    
    writer = csv.DictWriter(output, fieldnames=fieldnames, extrasaction='ignore')
    writer.writeheader()
    for rec in entries:
        writer.writerow(rec)
    
    output.seek(0)
    return send_file(
        io.BytesIO(output.getvalue().encode()),
        mimetype="text/csv",
        as_attachment=True,
        download_name="piggytree_entries.csv"
    )

@app.route("/api/categories")
def get_categories():
    return jsonify({
        "Quarterback (QB)": ["rush_rec_tds", "passing_yds", "passing_tds", "rushing_yds", "rushing_att",
            "passing_att", "passing_comps", "passing_ints", "fantasy_points",
            "passing_and_rushing_yds", "passing_long", "period_1_passing_yds",
            "period_1_rushing_yds", "period_1_passing_tds", "period_1_2_passing_yds",
            "period_1_2_rushing_yds", "period_1_2_passing_tds", "fumbles_lost",
            "25_pass_yds_each_quarter", "passing_comp_pct", "period_first_attempt_completions"],
        "Running Back (RB)": ["rush_rec_tds", "rushing_yds", "receiving_yds", "receiving_rec", "rushing_att",
            "fantasy_points", "rush_rec_yds", "receiving_long", "rushing_long",
            "period_first_touchdown_scored", "rushing_tds", "receiving_tds",
            "period_1_receiving_yds", "period_1_rushing_yds", "period_1_receiving_rec",
            "period_1_rush_rec_tds", "period_1_2_receiving_yds", "period_1_2_rushing_yds",
            "period_1_2_receiving_rec", "period_1_2_rush_rec_tds", "fumbles_lost"],
        "Wide Receiver (WR)": ["rush_rec_tds", "receiving_yds", "receiving_rec", "fantasy_points", "receiving_tgts",
            "receiving_long", "period_first_touchdown_scored", "period_1_receiving_yds",
            "period_1_receiving_rec", "period_1_rush_rec_tds", "period_1_2_receiving_yds",
            "period_1_2_receiving_rec", "period_1_2_rush_rec_tds", "fumbles_lost"],
        "Kicker (K)": ["field_goals_made", "extra_points_made", "kicking_points"],
        "NBA Player": ["points", "three_points_made", "rebounds", "assists", "pts_rebs_asts", "rebs_asts",
            "pts_rebs", "pts_asts", "double_doubles", "triple_doubles", "period_1_points",
            "period_1_rebounds", "period_1_assists", "period_1_three_points_made", "period_1_pts_rebs_asts",
            "fantasy_points", "turnovers", "steals", "free_throws_made", "period_1_2_points",
            "period_1_2_three_points_made", "period_1_2_assists", "period_1_2_pts_rebs_asts",
            "period_first_fg_attempt", "period_first_three_attempt", "period_1_first_5_min_pra",
            "period_1_first_5_min_pts", "offensive_rebounds"],
        "MLB Player": ["strikeouts", "fantasy_points", "pitch_outs", "hits_allowed", "runs_allowed",
            "walks_allowed", "period_1_strikeouts", "period_1_total_runs_allowed", "period_1_pitch_count",
            "period_1_batters_faced", "period_1_hits_allowed", "period_1_2_3_total_runs_allowed",
            "period_first_pitch_of_game_velocity"],
        "NFL Defense Player": ["sacks", "tackles_and_assists", "assists", "tackles"]
    })

@app.route("/api/teams")
def get_teams():
    nfl_teams = [
        "Arizona Cardinals", "Atlanta Falcons", "Baltimore Ravens", "Buffalo Bills", "Carolina Panthers",
        "Chicago Bears", "Cincinnati Bengals", "Cleveland Browns", "Dallas Cowboys", "Denver Broncos",
        "Detroit Lions", "Green Bay Packers", "Houston Texans", "Indianapolis Colts", "Jacksonville Jaguars",
        "Kansas City Chiefs", "Las Vegas Raiders", "Los Angeles Chargers", "Los Angeles Rams", "Miami Dolphins",
        "Minnesota Vikings", "New England Patriots", "New Orleans Saints", "New York Giants", "New York Jets",
        "Philadelphia Eagles", "Pittsburgh Steelers", "San Francisco 49ers", "Seattle Seahawks",
        "Tampa Bay Buccaneers", "Tennessee Titans", "Washington Commanders"
    ]
    nba_teams = [
        "Atlanta Hawks", "Boston Celtics", "Brooklyn Nets", "Charlotte Hornets", "Chicago Bulls",
        "Cleveland Cavaliers", "Dallas Mavericks", "Denver Nuggets", "Detroit Pistons", "Golden State Warriors",
        "Houston Rockets", "Indiana Pacers", "Los Angeles Clippers", "Los Angeles Lakers", "Memphis Grizzlies",
        "Miami Heat", "Milwaukee Bucks", "Minnesota Timberwolves", "New Orleans Pelicans", "New York Knicks",
        "Oklahoma City Thunder", "Orlando Magic", "Philadelphia 76ers", "Phoenix Suns", "Portland Trail Blazers",
        "Sacramento Kings", "San Antonio Spurs", "Toronto Raptors", "Utah Jazz", "Washington Wizards"
    ]
    mlb_teams = [
        "Arizona Diamondbacks", "Atlanta Braves", "Baltimore Orioles", "Boston Red Sox", "Chicago Cubs",
        "Chicago White Sox", "Cincinnati Reds", "Cleveland Guardians", "Colorado Rockies", "Detroit Tigers",
        "Houston Astros", "Kansas City Royals", "Los Angeles Angels", "Los Angeles Dodgers", "Miami Marlins",
        "Milwaukee Brewers", "Minnesota Twins", "New York Yankees", "New York Mets", "Oakland Athletics",
        "Philadelphia Phillies", "Pittsburgh Pirates", "San Diego Padres", "San Francisco Giants", "Seattle Mariners",
        "St. Louis Cardinals", "Tampa Bay Rays", "Texas Rangers", "Toronto Blue Jays", "Washington Nationals"
    ]
    return jsonify(sorted(nfl_teams + nba_teams + mlb_teams))

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)

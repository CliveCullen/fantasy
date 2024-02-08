import sqlite3

class Player:
    def __init__(self, name, country, value, position, call_up="start", supersub="no", tackles=0, conceded_penalties=0, defenders_beaten=0, metres_carried=0,
                 kick_50_22=0, lineout_steal=0, breakdown_steal=0, try_=0, assists=0, conversion=0, penalty=0,
                 drop_goal=0, yellow_cards=0, red_cards=0):
        self.name = name
        self.country = country
        self.value = value
        self.position = position
        self.call_up = call_up
        self.supersub = supersub
        self.tackles = tackles
        self.conceded_penalties = conceded_penalties
        self.defenders_beaten = defenders_beaten if defenders_beaten is not None else 0  # Ensure it's not None
        self.metres_carried = metres_carried
        self.kick_50_22 = kick_50_22
        self.lineout_steal = lineout_steal
        self.breakdown_steal = breakdown_steal
        self.try_ = try_
        self.assists = assists
        self.conversion = conversion
        self.penalty = penalty
        self.drop_goal = drop_goal
        self.yellow_cards = yellow_cards
        self.red_cards = red_cards
        self.is_captain = False  # Added attribute for captaincy

def get_required_position_count(position):
    position_counts = {
        "back_three": 3,
        "centre": 2,
        "fly_half": 1,
        "scrum_half": 1,
        "back_row": 3,
        "second_row": 2,
        "prop": 2,
        "hooker": 1
    }
    return position_counts.get(position, 0)

def read_players_from_database():
    players = []
    conn = sqlite3.connect('players.db')
    c = conn.cursor()
    c.execute("SELECT name, country, value, position, call_up, supersub, tackles, conceded_penalties, defenders_beaten, metres_carried, "
              "kick_50_22, lineout_steal, breakdown_steal, try, assists, conversion, penalty, drop_goal FROM players")
    rows = c.fetchall()
    for row in rows:
        players.append(Player(*row))
    conn.close()
    return players

def update_players_in_database(players):
    conn = sqlite3.connect('players.db')
    c = conn.cursor()
    for player in players:
        c.execute("UPDATE players SET tackles = ?, conceded_penalties = ?, defenders_beaten = ?, metres_carried = ?, "
                  "kick_50_22 = ?, lineout_steal = ?, breakdown_steal = ?, try = ?, assists = ?, conversion = ?, "
                  "penalty = ?, drop_goal = ?, call_up = ?, supersub = ? WHERE name = ?",
                  (player.tackles, player.conceded_penalties, player.defenders_beaten, player.metres_carried,
                   player.kick_50_22, player.lineout_steal, player.breakdown_steal, player.try_, player.assists,
                   player.conversion, player.penalty, player.drop_goal, player.call_up, player.supersub, player.name))
    conn.commit()
    conn.close()

def calculate_expected_points(player):
    # Handle case where conceded_penalties might be None
    conceded_penalties = int(player.conceded_penalties) if player.conceded_penalties is not None else 0

    expected_points = (
            int(player.tackles) * 1 +
            conceded_penalties * (-1) +
            int(player.defenders_beaten) * 2 +
            int(player.metres_carried) // 10 +
            int(player.kick_50_22) * 7 +
            int(player.lineout_steal) * 7 +
            int(player.breakdown_steal) * 5 +
            int(player.try_) * 10 +
            int(player.assists) * 4 +
            int(player.conversion) * 2 +
            int(player.penalty) * 3 +
            int(player.drop_goal) * 5 -
            int(player.yellow_cards) * 3 -
            int(player.red_cards) * 6 
    )
    return expected_points

def select_team(players, budget):
    team = []
    remaining_budget = budget
    selected_positions = {"back_three": 0, "centre": 0, "fly_half": 0, "scrum_half": 0, "back_row": 0, "second_row": 0,
                          "prop": 0, "hooker": 0}
    country_counts = {country: 0 for country in ["Ireland", "France", "Wales", "Scotland", "England", "Italy"]}
    captain = None
    supersub = None

    # Sort players by expected points in descending order
    players.sort(key=lambda x: calculate_expected_points(x), reverse=True)

    # Select the main team
    for player in players:
        if len(team) >= 15:
            break  # Exit loop if team is complete
        if player.value <= remaining_budget:
            if player.call_up == "start" and selected_positions[player.position] < get_required_position_count(player.position):
                team.append(player)
                remaining_budget -= player.value
                selected_positions[player.position] += 1
                country_counts[player.country] += 1
            elif player.call_up == "sub" and not supersub:
                supersub = player
                remaining_budget -= player.value

    # If the team doesn't have a captain yet, assign the highest-scoring player as captain
    if not captain and team:
        captain = max(team, key=lambda x: calculate_expected_points(x))
        team.remove(captain)  # Remove the captain from the team to ensure it's added back at the beginning

    # Ensure the team has exactly 16 players (including captain and supersub)
    while len(team) < 15:
        max_points = float('-inf')
        player_to_add = None
        for player in players:
            if player not in team and player.value <= remaining_budget:
                if player.call_up == "start" and selected_positions[player.position] < get_required_position_count(player.position):
                    if calculate_expected_points(player) > max_points:
                        max_points = calculate_expected_points(player)
                        player_to_add = player
                elif player.call_up == "sub" and not supersub:
                    if calculate_expected_points(player) * 4 <= remaining_budget:
                        if calculate_expected_points(player) > max_points:
                            max_points = calculate_expected_points(player)
                            player_to_add = player
        if player_to_add:
            team.append(player_to_add)
            remaining_budget -= player_to_add.value
            if player_to_add.call_up == "start":
                selected_positions[player_to_add.position] += 1
                country_counts[player_to_add.country] += 1
            else:
                supersub = player_to_add

    # Add the captain back to the team
    if captain:
        team.insert(0, captain)
        remaining_budget -= captain.value

    # If supersub was not assigned earlier, assign the highest-scoring available player as supersub
    if not supersub:
        for player in players:
            if player not in team and player.call_up == "sub" and player.value <= remaining_budget:
                supersub = player
                remaining_budget -= player.value
                break

    # Ensure the team stays within budget by replacing players with the least impact on points
    while remaining_budget < 0:
        min_points_player = min(team, key=lambda x: calculate_expected_points(x))
        remaining_budget += min_points_player.value
        team.remove(min_points_player)

    # Write selections to file
    write_selections_to_file(team, captain, supersub, budget - remaining_budget)

    return team, captain, supersub, budget - remaining_budget

def write_selections_to_file(team, captain, supersub, total_value):
    with open('selected_team.txt', 'w') as file:
        file.write("Selected Team:\n")
        total_points = 0
        for player in team:
            points = calculate_expected_points(player)
            if player.is_captain:
                file.write(f"Captain: {player.name} ({player.country}), Position: {player.position}, Call-up: {player.call_up}, Value: {player.value}, Points: {points}\n")
            elif player == supersub:
                file.write(f"Supersub: {player.name} ({player.country}), Position: {player.position}, Call-up: {player.call_up}, Value: {player.value}, Points: {points}\n")
            else:
                file.write(f"{player.name} ({player.country}), Position: {player.position}, Call-up: {player.call_up}, Value: {player.value}, Points: {points}\n")
            total_points += points
        if captain:
            captain_points = calculate_expected_points(captain) * 2
            total_points += captain_points
        if supersub:
            supersub_points = calculate_expected_points(supersub) * 4
            total_points += supersub_points
        file.write(f"Total Points of the Selected Team: {total_points}\n")
        file.write(f"Total Value of the Selected Team: {total_value}\n")

def main():
    players = read_players_from_database()
    budget = 239.8  # Budget for round 2
    team, captain, supersub, total_value = select_team(players, budget)

    write_selections_to_file(team, captain, supersub, total_value)

    print("Selection written to file selected_team.txt")

    # Update the database with adjusted values
    update_players_in_database(players)

if __name__ == "__main__":
    main()

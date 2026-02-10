# import pandas as pd
# import mysql.connector  # Richiede: pip install mysql-connector-python
# import re
#
# # --- CONFIGURAZIONE FILE ---
# FILE_GIOCATORI = 'giocatori1.txt'
# FILE_PARTITE = 'matches_serie_A.csv'
#
# # --- CONFIGURAZIONE MARIADB ---
# DB_CONFIG = {
#     'host': 'localhost',  # Di solito è localhost
#     'user': 'root',  # Il tuo username di MariaDB
#     'password': 'password',  # LA TUA PASSWORD
#     'database': 'serieA'  # Crea questo DB vuoto su DBeaver prima di lanciare lo script!
# }
#
#
# def main():
#     print("--- INIZIO CREAZIONE DATABASE SU MARIADB ---")
#
#     # 1. Caricamento Dati
#     print("1. Caricamento file CSV/TXT...")
#     try:
#         # Tenta di leggere con header alla riga 1
#         df_players = pd.read_csv(FILE_GIOCATORI, sep='\t', header=1)
#         if 'Player' not in df_players.columns:
#             df_players = pd.read_csv(FILE_GIOCATORI, sep='\t', header=0)
#     except Exception as e:
#         print(f"Errore lettura file giocatori: {e}")
#         return
#
#     try:
#         df_matches = pd.read_csv(FILE_PARTITE)
#     except Exception as e:
#         print(f"Errore lettura file partite: {e}")
#         return
#
#     # 2. Filtro e Mappatura (Identico a prima)
#     print("2. Elaborazione dati...")
#     df_matches_2025 = df_matches[df_matches['Season'] == 2025].copy()
#
#     teams_matches = sorted(df_matches_2025['Team'].unique())
#     teams_players = sorted(df_players['Squad'].dropna().unique())
#
#     mapping = {}
#     for tm in teams_matches:
#         if tm in teams_players:
#             mapping[tm] = tm
#         elif tm == 'Internazionale':
#             mapping[tm] = 'Inter'
#         else:
#             found = False
#             for tp in teams_players:
#                 if tp in tm or tm in tp:
#                     mapping[tm] = tp
#                     found = True
#                     break
#             if not found:
#                 print(f"ATTENZIONE: Nessuna corrispondenza trovata per '{tm}'")
#
#     # 3. Connessione al Database
#     print("3. Connessione a MariaDB...")
#     try:
#         conn = mysql.connector.connect(**DB_CONFIG)
#         cursor = conn.cursor()
#     except mysql.connector.Error as err:
#         print(f"Errore di connessione: {err}")
#         print("Verifica di aver creato il database vuoto e che user/password siano corretti.")
#         return
#
#     # 4. Creazione Tabelle (Reset iniziale)
#     # Nota: L'ordine di cancellazione è importante per le Foreign Keys
#     cursor.execute("DROP TABLE IF EXISTS performances")
#     cursor.execute("DROP TABLE IF EXISTS events")
#     cursor.execute("DROP TABLE IF EXISTS matches")
#     cursor.execute("DROP TABLE IF EXISTS players")
#     cursor.execute("DROP TABLE IF EXISTS teams")
#
#     print("Creazione tabelle...")
#
#     cursor.execute('''
#     CREATE TABLE teams (
#         id INT AUTO_INCREMENT PRIMARY KEY,
#         name VARCHAR(100) UNIQUE
#     )''')
#
#     cursor.execute('''
#     CREATE TABLE players (
#         id INT AUTO_INCREMENT PRIMARY KEY,
#         name VARCHAR(100),
#         team_id INT,
#         role VARCHAR(50),
#         weight_goal FLOAT,
#         weight_assist FLOAT,
#         weight_yellow FLOAT,
#         weight_red FLOAT,
#         FOREIGN KEY(team_id) REFERENCES teams(id)
#     )''')
#
#     cursor.execute('''
#     CREATE TABLE matches (
#         id INT AUTO_INCREMENT PRIMARY KEY,
#         giornata INT,
#         home_team_id INT,
#         away_team_id INT,
#         home_score INT DEFAULT NULL,
#         away_score INT DEFAULT NULL,
#         played TINYINT DEFAULT 0,
#         FOREIGN KEY(home_team_id) REFERENCES teams(id),
#         FOREIGN KEY(away_team_id) REFERENCES teams(id)
#     )''')
#
#     cursor.execute('''
#     CREATE TABLE events (
#         id INT AUTO_INCREMENT PRIMARY KEY,
#         match_id INT,
#         player_id INT,
#         type VARCHAR(50),
#         minute INT,
#         FOREIGN KEY(match_id) REFERENCES matches(id),
#         FOREIGN KEY(player_id) REFERENCES players(id)
#     )''')
#
#     cursor.execute('''
#     CREATE TABLE performances (
#         id INT AUTO_INCREMENT PRIMARY KEY,
#         match_id INT,
#         player_id INT,
#         vote FLOAT,
#         FOREIGN KEY(match_id) REFERENCES matches(id),
#         FOREIGN KEY(player_id) REFERENCES players(id)
#     )''')
#
#     # 5. Inserimento Dati
#     print("4. Popolamento database...")
#
#     # Teams
#     canonical_teams = sorted(list(set(mapping.values())))
#     team_to_id = {}
#
#     sql_team = "INSERT INTO teams (name) VALUES (%s)"
#
#     for name in canonical_teams:
#         cursor.execute(sql_team, (name,))
#         team_to_id[name] = cursor.lastrowid  # Recupera l'ID appena generato
#
#     # Players
#     count_players = 0
#     sql_player = '''
#         INSERT INTO players (name, team_id, role, weight_goal, weight_assist, weight_yellow, weight_red)
#         VALUES (%s, %s, %s, %s, %s, %s, %s)
#     '''
#
#     for index, row in df_players.iterrows():
#         squad_name = row['Squad']
#         if pd.isna(squad_name) or squad_name not in team_to_id:
#             continue
#
#         tid = team_to_id[squad_name]
#
#         gls = float(row['Gls']) if pd.notna(row['Gls']) else 0.0
#         ast = float(row['Ast']) if pd.notna(row['Ast']) else 0.0
#         yel = float(row['CrdY']) if pd.notna(row['CrdY']) else 0.0
#         red = float(row['CrdR']) if pd.notna(row['CrdR']) else 0.0
#
#         cursor.execute(sql_player, (row['Player'], tid, row['Pos'], gls, ast, yel, red))
#         count_players += 1
#
#     # Matches
#     df_schedule = df_matches_2025[df_matches_2025['Venue'] == 'Home']
#     count_matches = 0
#     sql_match = '''
#         INSERT INTO matches (giornata, home_team_id, away_team_id, played)
#         VALUES (%s, %s, %s, 0)
#     '''
#
#     for index, row in df_schedule.iterrows():
#         home_raw = row['Team']
#         away_raw = row['Opponent']
#
#         if home_raw in mapping and away_raw in mapping:
#             hid = team_to_id[mapping[home_raw]]
#             aid = team_to_id[mapping[away_raw]]
#
#             try:
#                 giornata = int(re.search(r'\d+', str(row['Round'])).group())
#             except:
#                 giornata = 0
#
#             cursor.execute(sql_match, (giornata, hid, aid))
#             count_matches += 1
#
#     conn.commit()
#     conn.close()
#
#     print(f"--- COMPLETATO! ---")
#     print(f"Squadre inserite: {len(team_to_id)}")
#     print(f"Giocatori inseriti: {count_players}")
#     print(f"Partite in calendario: {count_matches}")
#
#
# if __name__ == "__main__":
#     main()
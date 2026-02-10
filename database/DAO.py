from database.DB_connect import DBConnect


class DatabaseManager:
    def __init__(self):
        self.config_file = 'database/connector.cnf'

    def reset_simulation(self):
        """Resetta la stagione: cancella eventi, voti e risultati delle partite."""
        conn = self.get_connection()
        cursor = conn.cursor()
        try:
            # 1. Cancella tutti i dati delle prestazioni
            cursor.execute("DELETE FROM performances")

            # 2. Cancella tutti gli eventi
            cursor.execute("DELETE FROM events")

            # 3. Resetta le partite
            cursor.execute("""
                UPDATE matches 
                SET home_score = NULL, away_score = NULL, played = 0
            """)

            conn.commit()
            print("--- Stagione resettata con successo! ---")
        except Exception as e:
            conn.rollback()
            print(f"Errore durante il reset: {e}")
        finally:
            conn.close()


    def get_connection(self):
        return DBConnect.get_connection()

    def get_schedule(self, giornata):
        """Recupera le partite di una specifica giornata."""
        conn = self.get_connection()
        cursor = conn.cursor(dictionary=True)
        query = """
            SELECT m.id, m.home_score, m.away_score, m.played,
                   t1.name as home_team, t1.id as home_id,
                   t2.name as away_team, t2.id as away_id
            FROM matches m
            JOIN teams t1 ON m.home_team_id = t1.id
            JOIN teams t2 ON m.away_team_id = t2.id
            WHERE m.giornata = %s
        """
        cursor.execute(query, (giornata,))
        results = cursor.fetchall()
        conn.close()
        return results

    def get_team_players(self, team_id):
        """Recupera i giocatori di una squadra con le loro statistiche."""
        conn = self.get_connection()
        cursor = conn.cursor(dictionary=True)
        query = "SELECT * FROM players WHERE team_id = %s"
        cursor.execute(query, (team_id,))
        results = cursor.fetchall()
        conn.close()
        return results

    def save_match_result(self, match_id, home_goals, away_goals, events, performances):
        """Salva risultato, eventi (gol/cartellini) e voti in una transazione unica."""
        conn = self.get_connection()
        cursor = conn.cursor()

        try:
            # 1. Aggiorna Partita
            cursor.execute("""
                UPDATE matches SET home_score=%s, away_score=%s, played=1 
                WHERE id=%s
            """, (home_goals, away_goals, match_id))

            # 2. Inserisci Eventi
            event_sql = "INSERT INTO events (match_id, player_id, type, minute) VALUES (%s, %s, %s, %s)"
            cursor.executemany(event_sql, events)

            # 3. Inserisci Voti
            perf_sql = "INSERT INTO performances (match_id, player_id, vote) VALUES (%s, %s, %s)"
            cursor.executemany(perf_sql, performances)

            conn.commit()
        except Exception as e:
            conn.rollback()
            print(f"Errore salvataggio match {match_id}: {e}")
        finally:
            conn.close()

    def get_match_details(self, match_id):
        """Recupera gli eventi di una partita per il popup, quando si clicca una partita."""
        conn = self.get_connection()
        cursor = conn.cursor(dictionary=True)
        query = """
            SELECT e.type, e.minute, p.name, t.name as team_name
            FROM events e
            JOIN players p ON e.player_id = p.id
            JOIN teams t ON p.team_id = t.id
            WHERE e.match_id = %s
            ORDER BY e.minute ASC
        """
        cursor.execute(query, (match_id,))
        results = cursor.fetchall()
        conn.close()
        return results

    def get_standings(self):
        """Calcola la classifica dinamica."""
        conn = self.get_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT * FROM matches WHERE played = 1")
        matches = cursor.fetchall()

        cursor.execute("SELECT id, name FROM teams")
        teams = cursor.fetchall()
        conn.close()
        return teams, matches

    def get_top_scorers(self, limit=15):
        """Restituisce la classifica marcatori."""
        conn = self.get_connection()
        cursor = conn.cursor(dictionary=True)
        query = """
            SELECT p.name, t.name as team, COUNT(*) as count
            FROM events e
            JOIN players p ON e.player_id = p.id
            JOIN teams t ON p.team_id = t.id
            WHERE e.type = 'GOAL'
            GROUP BY p.id
            ORDER BY count DESC, p.name ASC
            LIMIT %s
        """
        cursor.execute(query, (limit,))
        results = cursor.fetchall()
        conn.close()
        return results

    def get_top_assists(self, limit=15):
        """Restituisce la classifica assist."""
        conn = self.get_connection()
        cursor = conn.cursor(dictionary=True)
        query = """
            SELECT p.name, t.name as team, COUNT(*) as count
            FROM events e
            JOIN players p ON e.player_id = p.id
            JOIN teams t ON p.team_id = t.id
            WHERE e.type = 'ASSIST'
            GROUP BY p.id
            ORDER BY count DESC, p.name ASC
            LIMIT %s
        """
        cursor.execute(query, (limit,))
        results = cursor.fetchall()
        conn.close()
        return results

    def get_totw(self, giornata):
        """Trova i migliori giocatori della giornata."""
        conn = self.get_connection()
        cursor = conn.cursor(dictionary=True)
        # Prende il miglior portiere, migliori 4 difensori, 3 centrocampisti, 3 attaccanti ---> 4-3-3
        query = """
            SELECT p.name, p.role, perf.vote, t.name as team
            FROM performances perf
            JOIN matches m ON perf.match_id = m.id
            JOIN players p ON perf.player_id = p.id
            JOIN teams t ON p.team_id = t.id
            WHERE m.giornata = %s
            ORDER BY perf.vote DESC
        """
        cursor.execute(query, (giornata,))
        results = cursor.fetchall()
        conn.close()
        return results
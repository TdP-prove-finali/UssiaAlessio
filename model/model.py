import random


class MatchSimulator:
    def __init__(self, db_manager):
        self.db = db_manager

    def simulate_day(self, giornata):
        matches = self.db.get_schedule(giornata)
        for match in matches:
            if match['played'] == 0:
                self._simulate_single_match(match)

    def _simulate_single_match(self, match):
        home_players = self.db.get_team_players(match['home_id'])
        away_players = self.db.get_team_players(match['away_id'])

        # 1. Calcolo Risultato (Semplificato basato sulla fortuna per ora) --> possibile modifica
        home_goals = self._poisson_goals() + (1 if random.random() > 0.6 else 0)  # Vantaggio casa
        away_goals = self._poisson_goals()

        events = []  # (match_id, player_id, type, minute)
        player_votes = {}  # player_id: voto

        # Inizializza giocatori con il 6.0 politico
        all_players = home_players + away_players
        for p in all_players:
            player_votes[p['id']] = 6.0

        # 2. Assegna Marcatori
        self._assign_goals(match['id'], home_goals, home_players, events, player_votes)
        self._assign_goals(match['id'], away_goals, away_players, events, player_votes)

        # 3. Assegna Cartellini (Casualità basata sull'aggressività)
        self._assign_cards(match['id'], all_players, events, player_votes)

        # 4. Bonus/Malus Risultato
        winner_bonus = 0.3
        if home_goals > away_goals:
            self._apply_team_bonus(home_players, player_votes, winner_bonus)
            self._apply_team_bonus(away_players, player_votes, -winner_bonus)
        elif away_goals > home_goals:
            self._apply_team_bonus(away_players, player_votes, winner_bonus)
            self._apply_team_bonus(home_players, player_votes, -winner_bonus)

        # Prepara dati voti per DB
        perf_data = [(match['id'], pid, round(v, 1)) for pid, v in player_votes.items()]

        self.db.save_match_result(match['id'], home_goals, away_goals, events, perf_data)

    def _poisson_goals(self): # num gol simulati, da cambiare in base alle squadre
        # Simula numero gol (0, 1, 2, 3...)
        r = random.random()
        if r < 0.25: return 0
        if r < 0.55: return 1
        if r < 0.80: return 2
        if r < 0.95: return 3
        return 4

    def _assign_goals(self, match_id, num_goals, team_players, events, votes):
        if num_goals == 0: return

        #scelta marcatori/assistman
        scorers_pool = []
        assisters_pool = []

        for p in team_players:
            # Aggiungi il giocatore n volte alla lista in base al suo peso gol
            weight = int(p['weight_goal'] * 100) + 1  # +1 per dare chance a tutti
            scorers_pool.extend([p] * weight)

            a_weight = int(p['weight_assist'] * 100) + 1
            assisters_pool.extend([p] * a_weight)

        for _ in range(num_goals):
            minute = random.randint(1, 90)

            # Scelta Marcatore
            scorer = random.choice(scorers_pool)
            events.append((match_id, scorer['id'], 'GOAL', minute))
            votes[scorer['id']] += 1.0

            # Scelta Assist (70% probabilità che ci sia assist)
            if random.random() < 0.7:
                assister = random.choice(assisters_pool)
                if assister['id'] != scorer['id']:  # No auto-assist
                    events.append((match_id, assister['id'], 'ASSIST', minute))
                    votes[assister['id']] += 0.5

    def _assign_cards(self, match_id, players, events, votes):
        for p in players:
            # Probabilità basata sullo storico
            prob_yellow = (p['weight_yellow'] / 38.0)
            if random.random() < prob_yellow:
                minute = random.randint(1, 90)
                events.append((match_id, p['id'], 'YELLOW', minute))
                votes[p['id']] -= 0.5

                # Doppia ammonizione -> Rosso?
                if random.random() < 0.05:
                    events.append((match_id, p['id'], 'RED', minute + 2))
                    votes[p['id']] -= 2.0

    def _apply_team_bonus(self, players, votes, amount):
        for p in players:
            votes[p['id']] += amount
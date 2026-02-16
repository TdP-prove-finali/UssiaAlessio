import random
import math


class MatchSimulator:
    def __init__(self, db_manager):
        self.db = db_manager

    def simulate_day(self, giornata):
        matches = self.db.get_schedule(giornata)
        for match in matches:
            if match['played'] == 0:
                self._simulate_single_match(match)

    def _calculate_team_strength(self, players):
        """
        Calcola la forza offensiva della squadra sommando
        il 'weight_goal' dei migliori 11 giocatori.
        """
        # Ordiniamo i giocatori per capacità realizzativa decrescente
        sorted_players = sorted(players, key=lambda p: p['weight_goal'], reverse=True)

        # Prendiamo solo i migliori 11
        top_11 = sorted_players[:11]

        strength = sum(p['weight_goal'] for p in top_11)

        # Evitiamo che la forza sia 0 (per squadre senza dati o neopromosse)
        return max(strength, 0.5)

    def _simulate_single_match(self, match):
        home_players = self.db.get_team_players(match['home_id'])
        away_players = self.db.get_team_players(match['away_id'])

        # 1. CALCOLO DELLA FORZA DELLE SQUADRE
        str_home = self._calculate_team_strength(home_players)
        str_away = self._calculate_team_strength(away_players)

        # 2. CALCOLO ASPETTATIVA GOL (xG) BASATO SULLA FORZA
        # Media gol serie A casalinga: ~1.45 | Trasferta: ~1.1

        # Fattore correttivo per evitare punteggi tennistici (es. 10-0)
        DAMPING_FACTOR = 0.6

        # Logica: (La mia forza / La tua forza) ^ Fattore
        ratio_home = math.pow(str_home / str_away, DAMPING_FACTOR)
        ratio_away = math.pow(str_away / str_home, DAMPING_FACTOR)

        # Lambda (Media gol attesi per questa partita)
        lambda_home = 1.45 * ratio_home
        lambda_away = 1.10 * ratio_away

        # Generiamo i gol usando la distribuzione di Poisson (la più usata nel calcio)
        home_goals = self._poisson(lambda_home)
        away_goals = self._poisson(lambda_away)

        events = []
        player_votes = {}

        # Inizializza voti base (6.0)
        all_players = home_players + away_players
        for p in all_players:
            player_votes[p['id']] = 6.0

        # 3. ASSEGNAZIONE MARCATORI (Pesata)
        self._assign_goals(match['id'], home_goals, home_players, events, player_votes)
        self._assign_goals(match['id'], away_goals, away_players, events, player_votes)

        # 4. ASSEGNAZIONE CARTELLINI (Basata sullo stress difensivo)
        # La squadra più debole tende a fare più falli per difendersi
        pressure_home = str_away / str_home  # Pressione subita dalla casa
        pressure_away = str_home / str_away  # Pressione subita dall'ospite

        self._assign_cards(match['id'], home_players, events, player_votes, pressure_factor=pressure_home)
        self._assign_cards(match['id'], away_players, events, player_votes, pressure_factor=pressure_away)

        # 5. BONUS/MALUS RISULTATO
        winner_bonus = 0.3
        if home_goals > away_goals:
            self._apply_team_bonus(home_players, player_votes, winner_bonus)
            self._apply_team_bonus(away_players, player_votes, -winner_bonus)
        elif away_goals > home_goals:
            self._apply_team_bonus(away_players, player_votes, winner_bonus)
            self._apply_team_bonus(home_players, player_votes, -winner_bonus)

        perf_data = [(match['id'], pid, round(v, 1)) for pid, v in player_votes.items()]
        self.db.save_match_result(match['id'], home_goals, away_goals, events, perf_data)

    def _poisson(self, lam):
        """Genera un numero casuale seguendo la distribuzione di Poisson con media 'lam'."""
        L = math.exp(-lam)
        k = 0
        p = 1.0
        while p > L:
            k += 1
            p *= random.random()
        return k - 1

    def _assign_goals(self, match_id, num_goals, team_players, events, votes):
        if num_goals == 0: return

        scorers_pool = []
        assisters_pool = []

        for p in team_players:
            # Peso gol aumentato per differenziare bomber da difensori
            weight = int(p['weight_goal'] * 1000) + 5
            scorers_pool.extend([p] * weight)

            a_weight = int(p['weight_assist'] * 1000) + 5
            assisters_pool.extend([p] * a_weight)

        if not scorers_pool: scorers_pool = team_players  # Fallback

        for _ in range(num_goals):
            minute = random.randint(1, 90)

            # Scelta Marcatore
            scorer = random.choice(scorers_pool)
            events.append((match_id, scorer['id'], 'GOAL', minute))
            votes[scorer['id']] += 1.001  # Bonus voto + Tie-breaker

            # Scelta Assist (70% probabilità)
            if random.random() < 0.7:
                assister = random.choice(assisters_pool)
                if assister['id'] != scorer['id']:
                    events.append((match_id, assister['id'], 'ASSIST', minute))
                    votes[assister['id']] += 0.5001

    def _assign_cards(self, match_id, players, events, votes, pressure_factor=1.0):

        base_yellow_prob = 1.0 / 35.0

        adjusted_prob = base_yellow_prob * min(pressure_factor, 1.3)

        cards_given = 0
        max_cards_per_team = random.choice([0, 1, 1, 2, 2, 3, 3, 4, 5])
        random.shuffle(players)

        for p in players:
            if cards_given >= max_cards_per_team:
                break
            personal_risk = (p['weight_yellow'] * 1.5) + 0.5
            if random.random() < (adjusted_prob * personal_risk):
                minute = random.randint(1, 90)

                # Assegna Giallo
                events.append((match_id, p['id'], 'YELLOW', minute))
                votes[p['id']] -= 0.5
                cards_given += 1

                # Assegna Rosso (Molto raro: 2% probabilità se hai preso il giallo)
                if random.random() < 0.02:
                    events.append((match_id, p['id'], 'RED', minute + 2))
                    votes[p['id']] -= 2.0  # Voto crolla

    def _apply_team_bonus(self, players, votes, amount):
        for p in players:
            votes[p['id']] += amount
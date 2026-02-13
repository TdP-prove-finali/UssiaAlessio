import tkinter as tk
from tkinter import ttk, messagebox, Menu
import sys
import os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from database.DAO import DatabaseManager
from model.model import MatchSimulator


class SerieAApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Simulatore Serie A 2025")
        self.root.geometry("1100x650")

        self.db = DatabaseManager()
        self.sim = MatchSimulator(self.db)
        self.current_giornata = 1

        # Stile personalizzato per i bottoni di navigazione
        style = ttk.Style()
        style.theme_use('clam')
        style.configure("Treeview", rowheight=25)
        style.configure("Nav.TButton", font=('Arial', 12, 'bold'), width=3)  # Frecce
        style.configure("Day.TButton", font=('Arial', 11), width=15)  # Bottone Centrale

        # Creazione Tab
        self.notebook = ttk.Notebook(root)
        self.notebook.pack(fill='both', expand=True, padx=10, pady=10)

        # Tab 1: Calendario
        self.tab_schedule = ttk.Frame(self.notebook)
        self.notebook.add(self.tab_schedule, text='Calendario & Risultati')
        self._build_schedule_tab()

        # Tab 2: Classifica
        self.tab_standings = ttk.Frame(self.notebook)
        self.notebook.add(self.tab_standings, text='Classifica')
        self._build_standings_tab()

        # Tab 3: TOTW
        self.tab_totw = ttk.Frame(self.notebook)
        self.notebook.add(self.tab_totw, text='Squadra della Settimana')
        self._build_totw_tab()

        # Tab 4: Statistiche
        self.tab_stats = ttk.Frame(self.notebook)
        self.notebook.add(self.tab_stats, text='Statistiche Giocatori')
        self._build_stats_tab()

        # Calcolo iniziale classifica (tutto a 0)
        self.calculate_standings()

    def _build_schedule_tab(self):

        # --- FRAME ---
        frame_controls = ttk.Frame(self.tab_schedule)
        frame_controls.pack(fill='x', padx=10, pady=10)

        # --- SEZIONE NAVIGAZIONE GIORNATE  ---
        nav_frame = ttk.Frame(frame_controls)
        nav_frame.pack(side='left', padx=10)

        # Bottone Indietro
        self.btn_prev = ttk.Button(nav_frame, text="<<", style="Nav.TButton", command=self.prev_giornata)
        self.btn_prev.pack(side='left', padx=2)

        # Bottone Centrale
        self.btn_day = ttk.Button(nav_frame, text=f"Giornata {self.current_giornata}", style="Day.TButton",
                                  command=self.show_day_menu)
        self.btn_day.pack(side='left', padx=2)

        # Bottone Avanti
        self.btn_next = ttk.Button(nav_frame, text=">>", style="Nav.TButton", command=self.next_giornata)
        self.btn_next.pack(side='left', padx=2)

        # Menu a tendina nascosto (popup) per la selezione rapida
        self.day_menu = Menu(self.root, tearoff=0)
        for i in range(1, 39):
            self.day_menu.add_command(label=f"Giornata {i}", command=lambda x=i: self.jump_to_giornata(x))

        # Bottone Simula
        btn_sim = ttk.Button(frame_controls, text="Simula Questa Giornata", command=self.simula_giornata_corrente)
        btn_sim.pack(side='right')

        # Lista Partite
        columns = ('id', 'casa', 'score', 'ospite', 'stato')
        self.tree_matches = ttk.Treeview(self.tab_schedule, columns=columns, show='headings')

        self.tree_matches.heading('id', text='ID')
        self.tree_matches.heading('casa', text='Squadra Casa')
        self.tree_matches.heading('score', text='Risultato')
        self.tree_matches.heading('ospite', text='Squadra Ospite')
        self.tree_matches.heading('stato', text='Stato')

        self.tree_matches.column('id', width=0, stretch=False)
        self.tree_matches.column('casa', anchor='e', width=150)
        self.tree_matches.column('score', anchor='center', width=100)
        self.tree_matches.column('ospite', anchor='w', width=150)
        self.tree_matches.column('stato', anchor='center', width=100)

        self.tree_matches.pack(fill='both', expand=True, padx=10, pady=10)

        self.tree_matches.bind("<Double-1>", self.show_match_details)
        self.load_matches()

    def prev_giornata(self):
        if self.current_giornata > 1:
            self.current_giornata -= 1
            self.update_nav_ui()
            self.load_matches()

    def next_giornata(self):
        if self.current_giornata < 38:
            self.current_giornata += 1
            self.update_nav_ui()
            self.load_matches()

    def jump_to_giornata(self, g):
        self.current_giornata = g
        self.update_nav_ui()
        self.load_matches()

    def show_day_menu(self):
        try:
            x = self.btn_day.winfo_rootx()
            y = self.btn_day.winfo_rooty() + self.btn_day.winfo_height()
            self.day_menu.tk_popup(x, y)
        finally:
            self.day_menu.grab_release()

    def update_nav_ui(self):
        self.btn_day.config(text=f"Giornata {self.current_giornata}")

        # Disabilita frecce se siamo al limite
        if self.current_giornata == 1:
            self.btn_prev.state(['disabled'])
        else:
            self.btn_prev.state(['!disabled'])

        if self.current_giornata == 38:
            self.btn_next.state(['disabled'])
        else:
            self.btn_next.state(['!disabled'])

    def _build_standings_tab(self):
        columns = ('pos', 'team', 'pt', 'g', 'v', 'n', 'p', 'gf', 'gs')
        self.tree_standings = ttk.Treeview(self.tab_standings, columns=columns, show='headings')
        self.tree_standings.heading('pos', text='#')
        self.tree_standings.heading('team', text='Squadra')
        self.tree_standings.heading('pt', text='PT')
        self.tree_standings.heading('g', text='G')
        self.tree_standings.heading('v', text='V')
        self.tree_standings.heading('n', text='N')
        self.tree_standings.heading('p', text='P')
        self.tree_standings.heading('gf', text='GF')
        self.tree_standings.heading('gs', text='GS')

        self.tree_standings.column('pos', width=40, anchor='center')
        self.tree_standings.column('team', width=200)
        self.tree_standings.column('pt', width=50, anchor='center')
        self.tree_standings.column('g', width=40, anchor='center')
        self.tree_standings.column('v', width=40, anchor='center')
        self.tree_standings.column('n', width=40, anchor='center')
        self.tree_standings.column('p', width=40, anchor='center')
        self.tree_standings.column('gf', width=40, anchor='center')
        self.tree_standings.column('gs', width=40, anchor='center')

        self.tree_standings.pack(fill='both', expand=True, padx=10, pady=10)

        btn_refresh = ttk.Button(self.tab_standings, text="Aggiorna Classifica", command=self.calculate_standings)
        btn_refresh.pack(pady=5)

    def _build_totw_tab(self):
        self.lbl_totw_title = ttk.Label(self.tab_totw, text="Top XI", font=("Arial", 14, "bold"))
        self.lbl_totw_title.pack(pady=10)

        self.txt_totw = tk.Text(self.tab_totw, height=20, width=70)  # Un po' più larga
        self.txt_totw.pack(padx=10, pady=10)

        btn_frame = ttk.Frame(self.tab_totw)
        btn_frame.pack(pady=5)

        btn_show_totw = ttk.Button(btn_frame, text="Mostra Squadra della Giornata", command=self.show_totw)
        btn_show_totw.pack(side='left', padx=10)

        btn_show_toty = ttk.Button(btn_frame, text="Mostra SQUADRA DELL'ANNO", command=self.show_toty)
        btn_show_toty.pack(side='left', padx=10)

    def _build_stats_tab(self):
        frame_container = ttk.Frame(self.tab_stats)
        frame_container.pack(fill='both', expand=True, padx=10, pady=10)

        frame_scorers = ttk.LabelFrame(frame_container, text="Classifica Marcatori (Top 15)")
        frame_scorers.pack(side='left', fill='both', expand=True, padx=5)

        cols_stat = ('pos', 'name', 'team', 'count')
        self.tree_scorers = ttk.Treeview(frame_scorers, columns=cols_stat, show='headings')
        self.tree_scorers.heading('pos', text='#')
        self.tree_scorers.heading('name', text='Giocatore')
        self.tree_scorers.heading('team', text='Squadra')
        self.tree_scorers.heading('count', text='Gol')
        self.tree_scorers.column('pos', width=30, anchor='center')
        self.tree_scorers.column('name', width=150)
        self.tree_scorers.column('team', width=120)
        self.tree_scorers.column('count', width=50, anchor='center')
        self.tree_scorers.pack(fill='both', expand=True, padx=5, pady=5)

        frame_assists = ttk.LabelFrame(frame_container, text="Classifica Assist (Top 15)")
        frame_assists.pack(side='right', fill='both', expand=True, padx=5)

        self.tree_assists = ttk.Treeview(frame_assists, columns=cols_stat, show='headings')
        self.tree_assists.heading('pos', text='#')
        self.tree_assists.heading('name', text='Giocatore')
        self.tree_assists.heading('team', text='Squadra')
        self.tree_assists.heading('count', text='Assist')
        self.tree_assists.column('pos', width=30, anchor='center')
        self.tree_assists.column('name', width=150)
        self.tree_assists.column('team', width=120)
        self.tree_assists.column('count', width=50, anchor='center')
        self.tree_assists.pack(fill='both', expand=True, padx=5, pady=5)

        btn_refresh_stats = ttk.Button(self.tab_stats, text="Aggiorna Statistiche", command=self.update_player_stats)
        btn_refresh_stats.pack(pady=5)

    def load_matches(self, event=None):
        g = self.current_giornata

        for item in self.tree_matches.get_children():
            self.tree_matches.delete(item)

        matches = self.db.get_schedule(g)
        for m in matches:
            score = f"{m['home_score']} - {m['away_score']}" if m['played'] else "- vs -"
            status = "FINITA" if m['played'] else "DA GIOCARE"
            self.tree_matches.insert('', 'end', values=(m['id'], m['home_team'], score, m['away_team'], status))

        self.update_nav_ui()

    def simula_giornata_corrente(self):
        g = self.current_giornata

        if self.db.check_giornata_completata(g):
            messagebox.showinfo(
                "Simulazione Completata",
                f"La Giornata {g} è già stata giocata.\nI risultati sono definitivi."
            )
            return

        if g > 1:
            giornata_precedente = g - 1
            if not self.db.check_giornata_completata(giornata_precedente):
                messagebox.showwarning(
                    "Ordine Errato",
                    f"Non puoi simulare la Giornata {g} se non hai ancora giocato la Giornata {giornata_precedente}.\n\nTorna indietro e simula in ordine!"
                )
                return

        self.sim.simulate_day(g)
        messagebox.showinfo("Simulazione", f"Giornata {g} simulata con successo!")
        self.load_matches()
        self.calculate_standings()
        self.update_player_stats()

    def show_match_details(self, event):
        item = self.tree_matches.selection()
        if not item: return
        match_id = self.tree_matches.item(item, "values")[0]
        match_status = self.tree_matches.item(item, "values")[4]

        if match_status == "DA GIOCARE":
            messagebox.showinfo("Info", "Partita non ancora giocata.")
            return

        details = self.db.get_match_details(match_id)
        popup = tk.Toplevel(self.root)
        popup.title("Dettagli Partita")
        popup.geometry("400x300")
        txt = tk.Text(popup, padx=10, pady=10)
        txt.pack(fill='both', expand=True)
        txt.insert('end', "--- EVENTI DEL MATCH ---\n\n")
        for ev in details:
            minute = ev['minute']
            tipo = ev['type']
            player = ev['name']
            team = ev['team_name']
            icon = "⚽" if tipo == 'GOAL' else "👟" if tipo == 'ASSIST' else "🟨" if tipo == 'YELLOW' else "🟥"
            txt.insert('end', f"{minute}' {icon} {tipo}: {player} ({team})\n")
        txt.config(state='disabled')

    def calculate_standings(self):
        teams, matches = self.db.get_standings()
        table = {t['id']: {'name': t['name'], 'pt': 0, 'g': 0, 'v': 0, 'n': 0, 'p': 0, 'gf': 0, 'gs': 0} for t in teams}

        for m in matches:
            h, a = m['home_team_id'], m['away_team_id']
            hs, as_ = m['home_score'], m['away_score']

            table[h]['g'] += 1
            table[a]['g'] += 1
            table[h]['gf'] += hs
            table[h]['gs'] += as_
            table[a]['gf'] += as_
            table[a]['gs'] += hs

            if hs > as_:
                table[h]['pt'] += 3
                table[h]['v'] += 1
                table[a]['p'] += 1
            elif as_ > hs:
                table[a]['pt'] += 3
                table[a]['v'] += 1
                table[h]['p'] += 1
            else:
                table[h]['pt'] += 1
                table[h]['n'] += 1
                table[a]['pt'] += 1
                table[a]['n'] += 1

        sorted_table = sorted(
            table.values(),
            key=lambda x: (-x['pt'], -(x['gf'] - x['gs']), -x['gf'], x['name'])
        )

        for item in self.tree_standings.get_children():
            self.tree_standings.delete(item)

        for i, row in enumerate(sorted_table, 1):
            self.tree_standings.insert('', 'end', values=(
            i, row['name'], row['pt'], row['g'], row['v'], row['n'], row['p'], row['gf'], row['gs']))

    def update_player_stats(self):
        for item in self.tree_scorers.get_children():
            self.tree_scorers.delete(item)
        for item in self.tree_assists.get_children():
            self.tree_assists.delete(item)

        scorers = self.db.get_top_scorers()
        assists = self.db.get_top_assists()

        for i, row in enumerate(scorers, 1):
            self.tree_scorers.insert('', 'end', values=(i, row['name'], row['team'], row['count']))
        for i, row in enumerate(assists, 1):
            self.tree_assists.insert('', 'end', values=(i, row['name'], row['team'], row['count']))

    def show_totw(self):
        g = self.current_giornata
        players = self.db.get_totw(g)

        if not players:
            self.txt_totw.delete('1.0', 'end')
            self.txt_totw.insert('end', "Nessuna partita giocata in questa giornata.")
            return

        self.lbl_totw_title.config(text=f"Top XI - Giornata {g}")
        self.txt_totw.delete('1.0', 'end')

        keepers = [p for p in players if 'GK' in p['role']]
        defs = [p for p in players if 'DF' in p['role']]
        mids = [p for p in players if 'MF' in p['role']]
        fwds = [p for p in players if 'FW' in p['role']]

        best_gk = keepers[:1]
        best_df = defs[:4]
        best_mf = mids[:3]
        best_fw = fwds[:3]

        top_xi = best_gk + best_df + best_mf + best_fw

        self.txt_totw.insert('end', f"{'VOTO':<6} {'RUOLO':<10} {'NOME':<25} {'SQUADRA'}\n")
        self.txt_totw.insert('end', "-" * 60 + "\n")

        for p in top_xi:
            self.txt_totw.insert('end', f"{p['vote']:<6} {p['role']:<10} {p['name']:<25} {p['team']}\n")


    def show_toty(self):
        players = self.db.get_season_best_players(min_presenze=5)

        if not players:
            self.txt_totw.delete('1.0', 'end')
            self.txt_totw.insert('end',
                                 "Non ci sono abbastanza dati per la Squadra dell'Anno (servono almeno 5 giornate).")
            return

        self.lbl_totw_title.config(text="SQUADRA DELL'ANNO (Media Voto)")
        self.txt_totw.delete('1.0', 'end')

        # Filtra per ruolo
        keepers = [p for p in players if 'GK' in p['role']]
        defs = [p for p in players if 'DF' in p['role']]
        mids = [p for p in players if 'MF' in p['role']]
        fwds = [p for p in players if 'FW' in p['role']]

        # Formazione 4-3-3 (Prende i migliori per media voto)
        best_gk = keepers[:1]
        best_df = defs[:4]
        best_mf = mids[:3]
        best_fw = fwds[:3]

        top_xi = best_gk + best_df + best_mf + best_fw

        self.txt_totw.insert('end', f"{'MEDIA':<6} {'PRES':<6} {'RUOLO':<8} {'NOME':<25} {'SQUADRA'}\n")
        self.txt_totw.insert('end', "=" * 70 + "\n")

        if not top_xi:
            self.txt_totw.insert('end',
                                 "Non ci sono abbastanza giocatori per formare un 4-3-3 completo.\nSimula più giornate!")
            return

        for p in top_xi:
            # Formattiamo la media voto per mostrare solo 2 decimali (es. 7.45)
            media = f"{p['avg_vote']:.2f}"
            self.txt_totw.insert('end', f"{media:<6} {p['presenze']:<6} {p['role']:<8} {p['name']:<25} {p['team']}\n")


if __name__ == "__main__":
    root = tk.Tk()
    app = SerieAApp(root)
    root.mainloop()
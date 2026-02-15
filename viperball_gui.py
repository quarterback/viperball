#!/usr/bin/env python3
"""
Viperball Dynasty Manager - Desktop GUI

A complete dynasty mode manager for women's Viperball.

Usage:
    python viperball_gui.py

Features:
    - Dashboard: Season overview, standings, your team
    - Team Roster: View and manage your 36-player roster
    - Recruiting: Browse recruits, make offers, track commitments
    - Simulator: Simulate games and advance seasons
    - Dynasty Management: Save/load dynasty, track history
"""

import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import json
from pathlib import Path
from datetime import datetime
import sys

# Add scripts to path
sys.path.insert(0, str(Path(__file__).parent))

class ViperballDynasty:
    """Dynasty data model."""

    def __init__(self):
        self.current_year = 2027
        self.current_week = 1
        self.user_team = None
        self.schools = []
        self.conferences = []
        self.standings = {}
        self.recruiting_class = []
        self.dynasty_name = "New Dynasty"
        self.history = []

    def load_base_data(self):
        """Load schools and conferences from data files."""
        data_dir = Path(__file__).parent / 'data'

        # Load schools
        with open(data_dir / 'schools' / 'd1_non_football.json') as f:
            schools_data = json.load(f)
            self.schools = schools_data['schools']

        # Load conferences
        with open(data_dir / 'conferences.json') as f:
            conf_data = json.load(f)
            self.conferences = conf_data['conferences']

        # Initialize standings
        for school in self.schools:
            school_id = school['school_id']
            self.standings[school_id] = {
                'wins': 0,
                'losses': 0,
                'conf_wins': 0,
                'conf_losses': 0,
                'points_for': 0,
                'points_against': 0
            }

    def save_dynasty(self, filepath):
        """Save dynasty to JSON file."""
        data = {
            'dynasty_name': self.dynasty_name,
            'current_year': self.current_year,
            'current_week': self.current_week,
            'user_team': self.user_team,
            'standings': self.standings,
            'recruiting_class': self.recruiting_class,
            'history': self.history,
            'saved_at': datetime.now().isoformat()
        }

        with open(filepath, 'w') as f:
            json.dump(data, f, indent=2)

    def load_dynasty(self, filepath):
        """Load dynasty from JSON file."""
        with open(filepath, 'r') as f:
            data = json.load(f)

        self.dynasty_name = data['dynasty_name']
        self.current_year = data['current_year']
        self.current_week = data['current_week']
        self.user_team = data['user_team']
        self.standings = data['standings']
        self.recruiting_class = data.get('recruiting_class', [])
        self.history = data.get('history', [])


class ViperballGUI:
    """Main GUI application."""

    def __init__(self, root):
        self.root = root
        self.root.title("Viperball Dynasty Manager")
        self.root.geometry("1200x800")

        # Initialize dynasty
        self.dynasty = ViperballDynasty()
        self.dynasty.load_base_data()

        # Setup UI
        self.setup_menu()
        self.setup_toolbar()
        self.setup_tabs()

        # Show welcome screen
        self.show_welcome_screen()

    def setup_menu(self):
        """Create menu bar."""
        menubar = tk.Menu(self.root)
        self.root.config(menu=menubar)

        # File menu
        file_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="File", menu=file_menu)
        file_menu.add_command(label="New Dynasty", command=self.new_dynasty)
        file_menu.add_command(label="Load Dynasty", command=self.load_dynasty)
        file_menu.add_command(label="Save Dynasty", command=self.save_dynasty)
        file_menu.add_separator()
        file_menu.add_command(label="Exit", command=self.root.quit)

        # Tools menu
        tools_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Tools", menu=tools_menu)
        tools_menu.add_command(label="Generate All Rosters", command=self.generate_all_rosters)
        tools_menu.add_command(label="Generate Recruiting Class", command=self.generate_recruits)

    def setup_toolbar(self):
        """Create toolbar with dynasty info."""
        toolbar = ttk.Frame(self.root, relief=tk.RAISED, borderwidth=1)
        toolbar.pack(side=tk.TOP, fill=tk.X, padx=5, pady=5)

        # Dynasty info
        self.dynasty_label = ttk.Label(toolbar, text="No Dynasty Loaded", font=('Arial', 12, 'bold'))
        self.dynasty_label.pack(side=tk.LEFT, padx=10)

        ttk.Separator(toolbar, orient=tk.VERTICAL).pack(side=tk.LEFT, fill=tk.Y, padx=5)

        self.year_label = ttk.Label(toolbar, text="Year: 2027", font=('Arial', 10))
        self.year_label.pack(side=tk.LEFT, padx=10)

        self.week_label = ttk.Label(toolbar, text="Week: 1", font=('Arial', 10))
        self.week_label.pack(side=tk.LEFT, padx=10)

        # Quick actions
        ttk.Button(toolbar, text="Advance Week", command=self.advance_week).pack(side=tk.RIGHT, padx=5)
        ttk.Button(toolbar, text="Simulate Season", command=self.simulate_season).pack(side=tk.RIGHT, padx=5)

    def setup_tabs(self):
        """Create main tabbed interface."""
        self.notebook = ttk.Notebook(self.root)
        self.notebook.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        # Dashboard tab
        self.dashboard_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.dashboard_frame, text="📊 Dashboard")
        self.setup_dashboard()

        # Team Roster tab
        self.roster_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.roster_frame, text="👥 Team Roster")
        self.setup_roster()

        # Recruiting tab
        self.recruiting_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.recruiting_frame, text="🎓 Recruiting")
        self.setup_recruiting()

        # Standings tab
        self.standings_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.standings_frame, text="🏆 Standings")
        self.setup_standings()

        # History tab
        self.history_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.history_frame, text="📜 History")
        self.setup_history()

    def setup_dashboard(self):
        """Setup dashboard tab."""
        # Header
        header = ttk.Label(self.dashboard_frame, text="Dynasty Dashboard",
                          font=('Arial', 16, 'bold'))
        header.pack(pady=10)

        # Team info section
        team_frame = ttk.LabelFrame(self.dashboard_frame, text="Your Team", padding=10)
        team_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        self.team_info_text = tk.Text(team_frame, height=10, width=80, wrap=tk.WORD)
        self.team_info_text.pack(fill=tk.BOTH, expand=True)

        # Recent games section
        games_frame = ttk.LabelFrame(self.dashboard_frame, text="Recent Games", padding=10)
        games_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        self.recent_games_text = tk.Text(games_frame, height=8, width=80, wrap=tk.WORD)
        self.recent_games_text.pack(fill=tk.BOTH, expand=True)

        # Update dashboard
        self.update_dashboard()

    def setup_roster(self):
        """Setup roster tab."""
        # Header
        header = ttk.Label(self.roster_frame, text="Team Roster",
                          font=('Arial', 16, 'bold'))
        header.pack(pady=10)

        # Roster table
        table_frame = ttk.Frame(self.roster_frame)
        table_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        # Scrollbar
        scrollbar = ttk.Scrollbar(table_frame)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        # Treeview
        columns = ('#', 'Name', 'Pos', 'Year', 'Ht', 'Wt', 'SPD', 'KCK', 'LAT', 'TAC')
        self.roster_tree = ttk.Treeview(table_frame, columns=columns, show='headings',
                                       yscrollcommand=scrollbar.set)

        # Column headings
        for col in columns:
            self.roster_tree.heading(col, text=col)
            if col == 'Name':
                self.roster_tree.column(col, width=180)
            elif col == 'Pos':
                self.roster_tree.column(col, width=120)
            else:
                self.roster_tree.column(col, width=50)

        self.roster_tree.pack(fill=tk.BOTH, expand=True)
        scrollbar.config(command=self.roster_tree.yview)

        # Load roster button
        ttk.Button(self.roster_frame, text="Load Roster",
                  command=self.load_roster).pack(pady=10)

    def setup_recruiting(self):
        """Setup recruiting tab."""
        # Header
        header = ttk.Label(self.recruiting_frame, text="Recruiting Board",
                          font=('Arial', 16, 'bold'))
        header.pack(pady=10)

        # Info
        info = ttk.Label(self.recruiting_frame,
                        text="Browse and recruit the next generation of Viperball stars!")
        info.pack(pady=5)

        # Recruit table
        table_frame = ttk.Frame(self.recruiting_frame)
        table_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        # Scrollbar
        scrollbar = ttk.Scrollbar(table_frame)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        # Treeview
        columns = ('Name', 'Pos', 'Stars', 'Hometown', 'High School', 'Interest')
        self.recruit_tree = ttk.Treeview(table_frame, columns=columns, show='headings',
                                        yscrollcommand=scrollbar.set)

        for col in columns:
            self.recruit_tree.heading(col, text=col)
            if col in ['Name', 'High School']:
                self.recruit_tree.column(col, width=150)
            elif col == 'Hometown':
                self.recruit_tree.column(col, width=120)
            else:
                self.recruit_tree.column(col, width=80)

        self.recruit_tree.pack(fill=tk.BOTH, expand=True)
        scrollbar.config(command=self.recruit_tree.yview)

        # Actions
        action_frame = ttk.Frame(self.recruiting_frame)
        action_frame.pack(pady=10)

        ttk.Button(action_frame, text="Make Offer",
                  command=self.make_recruiting_offer).pack(side=tk.LEFT, padx=5)
        ttk.Button(action_frame, text="Generate New Class",
                  command=self.generate_recruits).pack(side=tk.LEFT, padx=5)

    def setup_standings(self):
        """Setup standings tab."""
        # Header
        header = ttk.Label(self.standings_frame, text="Conference Standings",
                          font=('Arial', 16, 'bold'))
        header.pack(pady=10)

        # Conference selector
        conf_frame = ttk.Frame(self.standings_frame)
        conf_frame.pack(pady=5)

        ttk.Label(conf_frame, text="Conference:").pack(side=tk.LEFT, padx=5)

        self.conf_var = tk.StringVar()
        conf_names = [c['name'] for c in self.dynasty.conferences]
        self.conf_combo = ttk.Combobox(conf_frame, textvariable=self.conf_var,
                                       values=conf_names, state='readonly', width=30)
        if conf_names:
            self.conf_combo.current(0)
        self.conf_combo.pack(side=tk.LEFT, padx=5)
        self.conf_combo.bind('<<ComboboxSelected>>', lambda e: self.update_standings())

        # Standings table
        table_frame = ttk.Frame(self.standings_frame)
        table_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        columns = ('Rank', 'Team', 'W', 'L', 'Conf', 'PF', 'PA', 'Diff')
        self.standings_tree = ttk.Treeview(table_frame, columns=columns, show='headings')

        for col in columns:
            self.standings_tree.heading(col, text=col)
            if col == 'Team':
                self.standings_tree.column(col, width=250)
            else:
                self.standings_tree.column(col, width=60)

        self.standings_tree.pack(fill=tk.BOTH, expand=True)

        # Update standings
        self.update_standings()

    def setup_history(self):
        """Setup history tab."""
        # Header
        header = ttk.Label(self.history_frame, text="Dynasty History",
                          font=('Arial', 16, 'bold'))
        header.pack(pady=10)

        # History text
        history_text_frame = ttk.Frame(self.history_frame)
        history_text_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        scrollbar = ttk.Scrollbar(history_text_frame)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        self.history_text = tk.Text(history_text_frame, wrap=tk.WORD,
                                    yscrollcommand=scrollbar.set)
        self.history_text.pack(fill=tk.BOTH, expand=True)
        scrollbar.config(command=self.history_text.yview)

        self.update_history()

    # === Event Handlers ===

    def show_welcome_screen(self):
        """Show welcome dialog."""
        welcome_msg = """Welcome to Viperball Dynasty Manager!

This is your command center for managing a women's Viperball dynasty.

Get started:
1. File → New Dynasty to create a new dynasty
2. Select your team
3. Start recruiting and simulating!

Features:
• Dashboard - Season overview and team info
• Team Roster - Manage your 36-player roster
• Recruiting - Browse and recruit high school players
• Standings - Track conference and league standings
• History - View your dynasty's history

Good luck, Coach!"""

        messagebox.showinfo("Welcome", welcome_msg)

    def new_dynasty(self):
        """Create a new dynasty."""
        # Team selection dialog
        dialog = tk.Toplevel(self.root)
        dialog.title("New Dynasty")
        dialog.geometry("600x500")
        dialog.transient(self.root)
        dialog.grab_set()

        ttk.Label(dialog, text="Select Your Team", font=('Arial', 14, 'bold')).pack(pady=10)

        # Search frame
        search_frame = ttk.Frame(dialog)
        search_frame.pack(pady=5)

        ttk.Label(search_frame, text="Search:").pack(side=tk.LEFT, padx=5)
        search_var = tk.StringVar()
        search_entry = ttk.Entry(search_frame, textvariable=search_var, width=30)
        search_entry.pack(side=tk.LEFT, padx=5)

        # Team list
        list_frame = ttk.Frame(dialog)
        list_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        scrollbar = ttk.Scrollbar(list_frame)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        team_listbox = tk.Listbox(list_frame, yscrollcommand=scrollbar.set, font=('Arial', 10))
        team_listbox.pack(fill=tk.BOTH, expand=True)
        scrollbar.config(command=team_listbox.yview)

        # Populate teams
        team_dict = {}
        for school in self.dynasty.schools:
            display_text = f"{school['school_name']} ({school['abbreviation']}) - {school['city']}, {school['state']}"
            team_dict[display_text] = school['school_id']
            team_listbox.insert(tk.END, display_text)

        def filter_teams(*args):
            query = search_var.get().lower()
            team_listbox.delete(0, tk.END)
            for display_text in team_dict.keys():
                if query in display_text.lower():
                    team_listbox.insert(tk.END, display_text)

        search_var.trace('w', filter_teams)

        def select_team():
            selection = team_listbox.curselection()
            if not selection:
                messagebox.showwarning("No Selection", "Please select a team.")
                return

            selected_text = team_listbox.get(selection[0])
            school_id = team_dict[selected_text]

            self.dynasty.user_team = school_id
            self.dynasty.dynasty_name = f"{selected_text.split('(')[0].strip()} Dynasty"

            dialog.destroy()
            self.update_all()

            messagebox.showinfo("Dynasty Created",
                              f"Dynasty created!\n\nYou are now coaching:\n{selected_text}")

        ttk.Button(dialog, text="Select Team", command=select_team).pack(pady=10)

    def load_dynasty(self):
        """Load a saved dynasty."""
        filepath = filedialog.askopenfilename(
            title="Load Dynasty",
            filetypes=[("Dynasty Files", "*.json"), ("All Files", "*.*")],
            defaultextension=".json"
        )

        if filepath:
            try:
                self.dynasty.load_dynasty(filepath)
                self.update_all()
                messagebox.showinfo("Success", f"Dynasty loaded!\n\n{self.dynasty.dynasty_name}")
            except Exception as e:
                messagebox.showerror("Error", f"Failed to load dynasty:\n{str(e)}")

    def save_dynasty(self):
        """Save current dynasty."""
        if not self.dynasty.user_team:
            messagebox.showwarning("No Dynasty", "Create or load a dynasty first.")
            return

        filepath = filedialog.asksaveasfilename(
            title="Save Dynasty",
            defaultextension=".json",
            filetypes=[("Dynasty Files", "*.json"), ("All Files", "*.*")]
        )

        if filepath:
            try:
                self.dynasty.save_dynasty(filepath)
                messagebox.showinfo("Success", "Dynasty saved successfully!")
            except Exception as e:
                messagebox.showerror("Error", f"Failed to save dynasty:\n{str(e)}")

    def advance_week(self):
        """Advance to next week."""
        if not self.dynasty.user_team:
            messagebox.showwarning("No Dynasty", "Create or load a dynasty first.")
            return

        # Simulate games for this week
        self.dynasty.current_week += 1

        if self.dynasty.current_week > 12:
            # Season over
            self.dynasty.current_week = 1
            self.dynasty.current_year += 1
            self.dynasty.history.append({
                'year': self.dynasty.current_year - 1,
                'result': 'Season completed'
            })
            messagebox.showinfo("Season Complete",
                              f"Season {self.dynasty.current_year - 1} complete!\n\nAdvancing to {self.dynasty.current_year}")

        self.update_all()
        messagebox.showinfo("Week Advanced", f"Advanced to Week {self.dynasty.current_week}")

    def simulate_season(self):
        """Simulate entire season."""
        if not self.dynasty.user_team:
            messagebox.showwarning("No Dynasty", "Create or load a dynasty first.")
            return

        result = messagebox.askyesno("Simulate Season",
                                     "Simulate the entire season?\n\nThis will advance to the next year.")

        if result:
            self.dynasty.current_week = 1
            self.dynasty.current_year += 1
            self.dynasty.history.append({
                'year': self.dynasty.current_year - 1,
                'result': 'Season simulated'
            })
            self.update_all()
            messagebox.showinfo("Season Simulated",
                              f"Season complete!\n\nNow in {self.dynasty.current_year}")

    def load_roster(self):
        """Load team roster."""
        if not self.dynasty.user_team:
            messagebox.showwarning("No Dynasty", "Create or load a dynasty first.")
            return

        # Load roster data
        roster_file = Path(__file__).parent / 'data' / 'teams' / f"{self.dynasty.user_team}.json"

        if not roster_file.exists():
            messagebox.showwarning("No Roster",
                                 f"Roster not generated yet for this team.\n\nGenerate it with:\npython scripts/generate_rosters.py --schools {self.dynasty.user_team}")
            return

        try:
            with open(roster_file) as f:
                team_data = json.load(f)

            # Clear existing
            for item in self.roster_tree.get_children():
                self.roster_tree.delete(item)

            # Add players
            for player in team_data['roster']['players']:
                self.roster_tree.insert('', tk.END, values=(
                    player['number'],
                    player['name'],
                    player['position'],
                    player['year'],
                    player['height'],
                    player['weight'],
                    player['stats']['speed'],
                    player['stats']['kicking'],
                    player['stats']['lateral_skill'],
                    player['stats']['tackling']
                ))

            messagebox.showinfo("Roster Loaded", f"Loaded {len(team_data['roster']['players'])} players")

        except Exception as e:
            messagebox.showerror("Error", f"Failed to load roster:\n{str(e)}")

    def generate_all_rosters(self):
        """Generate rosters for all teams."""
        result = messagebox.askyesno("Generate Rosters",
                                     "Generate rosters for all 102 teams?\n\nThis may take a minute.")

        if result:
            import subprocess
            try:
                subprocess.run(['python', 'scripts/generate_rosters.py', '--all'], check=True)
                messagebox.showinfo("Success", "All rosters generated!")
            except Exception as e:
                messagebox.showerror("Error", f"Failed to generate rosters:\n{str(e)}")

    def generate_recruits(self):
        """Generate recruiting class."""
        messagebox.showinfo("Coming Soon", "Recruiting class generation will be implemented in the next update!")

    def make_recruiting_offer(self):
        """Make an offer to a recruit."""
        selection = self.recruit_tree.selection()
        if not selection:
            messagebox.showwarning("No Selection", "Select a recruit first.")
            return

        messagebox.showinfo("Coming Soon", "Recruiting offers will be implemented in the next update!")

    def update_dashboard(self):
        """Update dashboard display."""
        self.team_info_text.delete('1.0', tk.END)

        if self.dynasty.user_team:
            # Find user's team
            team = next((s for s in self.dynasty.schools if s['school_id'] == self.dynasty.user_team), None)

            if team:
                info = f"{team['school_name']} {team['mascot']}\n"
                info += f"{team['city']}, {team['state']}\n"
                info += f"Conference: {team.get('conference_planned', 'Independent')}\n\n"

                # Record
                record = self.dynasty.standings.get(self.dynasty.user_team, {})
                info += f"Record: {record.get('wins', 0)}-{record.get('losses', 0)}\n"
                info += f"Conference: {record.get('conf_wins', 0)}-{record.get('conf_losses', 0)}\n"
                info += f"Points For: {record.get('points_for', 0)}\n"
                info += f"Points Against: {record.get('points_against', 0)}\n"

                self.team_info_text.insert('1.0', info)
        else:
            self.team_info_text.insert('1.0', "No dynasty loaded.\n\nCreate a new dynasty to get started!")

        self.recent_games_text.delete('1.0', tk.END)
        self.recent_games_text.insert('1.0', "No games played yet.\n\nAdvance the week to simulate games!")

    def update_standings(self):
        """Update standings display."""
        # Clear existing
        for item in self.standings_tree.get_children():
            self.standings_tree.delete(item)

        # Get selected conference
        conf_name = self.conf_var.get()
        if not conf_name:
            return

        conf = next((c for c in self.dynasty.conferences if c['name'] == conf_name), None)
        if not conf:
            return

        # Get teams in conference
        teams_data = []
        for school_id in conf['schools']:
            school = next((s for s in self.dynasty.schools if s['school_id'] == school_id), None)
            if school:
                record = self.dynasty.standings.get(school_id, {})
                teams_data.append({
                    'name': school['school_name'],
                    'wins': record.get('wins', 0),
                    'losses': record.get('losses', 0),
                    'conf_record': f"{record.get('conf_wins', 0)}-{record.get('conf_losses', 0)}",
                    'pf': record.get('points_for', 0),
                    'pa': record.get('points_against', 0),
                    'diff': record.get('points_for', 0) - record.get('points_against', 0)
                })

        # Sort by wins
        teams_data.sort(key=lambda t: (t['wins'], t['diff']), reverse=True)

        # Add to tree
        for i, team in enumerate(teams_data, 1):
            self.standings_tree.insert('', tk.END, values=(
                i,
                team['name'],
                team['wins'],
                team['losses'],
                team['conf_record'],
                team['pf'],
                team['pa'],
                team['diff']
            ))

    def update_history(self):
        """Update history display."""
        self.history_text.delete('1.0', tk.END)

        if not self.dynasty.history:
            self.history_text.insert('1.0', "No history yet.\n\nStart playing to build your dynasty's legacy!")
        else:
            for entry in self.dynasty.history:
                self.history_text.insert(tk.END, f"Year {entry['year']}: {entry['result']}\n")

    def update_all(self):
        """Update all displays."""
        # Update toolbar
        if self.dynasty.user_team:
            team = next((s for s in self.dynasty.schools if s['school_id'] == self.dynasty.user_team), None)
            if team:
                self.dynasty_label.config(text=f"🏈 {team['school_name']} {team['mascot']}")
        else:
            self.dynasty_label.config(text="No Dynasty Loaded")

        self.year_label.config(text=f"Year: {self.dynasty.current_year}")
        self.week_label.config(text=f"Week: {self.dynasty.current_week}")

        # Update all tabs
        self.update_dashboard()
        self.update_standings()
        self.update_history()


def main():
    """Run the GUI application."""
    root = tk.Tk()
    app = ViperballGUI(root)
    root.mainloop()


if __name__ == "__main__":
    main()

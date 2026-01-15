import tkinter as tk
from tkinter import scrolledtext, messagebox
import pandas as pd
import random

moves_df_global = None
full_battle_log = []

def load_pokemon_data():
    """
    Loads the pokemon data from pokemon.csv into a dataframe and returns it
    """
    df = pd.read_csv('pokemon.csv')
    return df

def load_moves_data():
    """
    Loads the moves data from moves.csv into a dataframe and returns it
    """
    df = pd.read_csv('moves.csv')
    return df

def find_pokemon_by_name(df, name):
    """
    Searches for a pokemon in the pokemon dataframe and returns the row containing the pokemon's data
    Returns None if the pokemon name given by the player doesn't exist
    """
    lower_name = name.lower()
    for index, row in df.iterrows():
        if str(row['name']).lower() == lower_name:
            return row
    return None

def get_level_proportional_moves(pokemon_row, moves_df, level=15):
    """
    Selects 4 moves for a pokemon to use based on its types and base stats and returns them
    """
    type1 = str(pokemon_row['type1']).lower()
    type2 = pokemon_row['type2'] if pd.notna(pokemon_row['type2']) else None
    # Gets all of the moves that the pokemon's primary type can use
    type_moves = moves_df[moves_df['type'].str.lower() == type1]
    if type2 is not None:
        # If the pokemon has a secondary type, gets the moves that the secondary type can use
        more_moves = moves_df[moves_df['type'].str.lower() == str(type2).lower()]
        type_moves = pd.concat([type_moves, more_moves])

    # Removing duplicate moves so the pokemon doesn't have to use the same moves every time
    seen = set()
    keep_rows = []
    for name in type_moves['name']:
        keep_rows.append(name not in seen)
        seen.add(name)
    type_moves = type_moves[keep_rows]

    # Calculates the moves allowed based on their power.
    # Either 15% of the pokemon's base stats or the base value of 40
    # This isn't what the actual pokemon games use, I only made it like this for my game.
    max_power = max(40, int(pokemon_row['base_total'] * 0.15))
    weak_moves = type_moves[type_moves['power'] <= max_power]

    if len(weak_moves) >= 4:
        return weak_moves.sample(4)
    final_moves = weak_moves.copy()

    if len(final_moves) < 4:
        strong_moves = type_moves[type_moves['power'] > max_power]
        need = min(4 - len(final_moves), len(strong_moves))
        if need > 0:
            extra = strong_moves.sample(need)
            final_moves = pd.concat([final_moves, extra])

    return final_moves.head(4)

def get_type_multiplier(move_type, def_type):
    """
    Contains a dictionary to reference the type effectiveness for different matchups
    Returns the type effectiveness for a move against a defending pokemon's type
    """
    # Most pokemon of a certain type follow a the same type effectiveness against another type, but some vary
    # So, I had to manually make one for all pokemon to follow
    chart = {
        ('electric', 'water'): 2.0, ('electric', 'ground'): 0.0,
        ('fire', 'grass'): 2.0, ('fire', 'water'): 0.5,
        ('water', 'fire'): 2.0, ('water', 'grass'): 0.5,
        ('grass', 'water'): 2.0, ('grass', 'fire'): 0.5,
        ('fighting', 'normal'): 2.0, ('fighting', 'flying'): 0.5,
        ('ground', 'electric'): 2.0, ('ground', 'flying'): 0.0,
        ('psychic', 'fighting'): 2.0, ('psychic', 'psychic'): 0.5,
        ('flying', 'fighting'): 2.0, ('flying', 'electric'): 0.5,
        ('poison', 'grass'): 2.0, ('poison', 'poison'): 0.5,
        ('bug', 'grass'): 2.0, ('bug', 'flying'): 0.5,
        ('rock', 'flying'): 2.0, ('rock', 'fighting'): 0.5,
        ('ghost', 'psychic'): 2.0, ('ghost', 'normal'): 0.0,
        ('dragon', 'dragon'): 2.0, ('ice', 'ground'): 2.0,
        ('normal', 'rock'): 0.5, ('normal', 'ghost'): 0.0}
    return chart.get((move_type.lower(), def_type.lower()), 1.0)

def calculate_damage(attacker, defender, move_power, move_type, attacker_type):
    """
    Calculates the damage that a move causes using a formula, and then returns it
    """
    base = ((2 * 50 / 5 + 2) * attacker['attack'] * move_power / max(1, defender['defense'])) / 50 + 2
    if str(move_type).lower() == str(attacker_type).lower():
        stab = 1.5 # STAB (Same-Type Attack Bonus) - If the move type is same as Pokemon type, the damage is multiplied by 1.5
    else:
        stab = 1.0
    type_mult = get_type_multiplier(str(move_type), str(defender['type1']))
    if pd.notna(defender['type2']):
        type_mult *= get_type_multiplier(str(move_type), str(defender['type2']))
    # For random variation to make it more realistic, I used random.uniform()
    damage = int(base * stab * type_mult * random.uniform(0.85, 1.0))
    return max(1, damage)

def write_battle_log():
    """
    Writes the complete battle history from full_battle_log to battle_log.txt
    """
    # I'm using the global keyword so it can access the shared battle history across all battles
    global full_battle_log

    # Creates a new file if battle_log.txt doesnt already exist
    try:
        with open('battle_log.txt', 'x') as f:
            f.write("POKEMON BATTLE LOG\n")
            f.write("=" * 50 + "\n")
            f.write("\n".join(full_battle_log))
    except FileExistsError:
        # File exists, adds the new log
        with open('battle_log.txt', 'w') as f:
            f.write("POKEMON BATTLE LOG")
            f.write("\n" + "=" * 50 + "\n") 
            f.write("\n".join(full_battle_log))

def create_pokemon_display_text(poke_row, moves_df):
    """
    Generates a formatted display of the pokemons stats including:
        Name, Pokedex number, types, generation, and legendary status
        Physical stats
        Base Battle stats
        Most powerful moves
    """
    moves_list = get_level_proportional_moves(poke_row, moves_df)
    text = ""
    text += "╔════════════════════════════════════════════════╗\n"
    text += "║           " + str(poke_row['name']).upper() + " #" + str(poke_row['pokedex_number']).zfill(3) + "              ║\n"
    text += "╠════════════════════════════════════════════════╣\n"

    type_text = str(poke_row['type1']).title()
    if pd.notna(poke_row['type2']):
        type_text = type_text + "/" + str(poke_row['type2']).title()
    text += "║ Type: " + type_text + "\n"
    legendary_text = "YES" if poke_row['is_legendary'] else "NO "
    text += "║ Gen: " + str(poke_row['generation']) + " | Legendary: " + legendary_text + "\n"

    text += "╠════════════════════════════════════════════════╣\n"

    text += "║ Height: " + str(poke_row['height_m']) + "m  Weight: " + str(poke_row['weight_kg']) + "kg" + "\n"
    text += "║ Capture Rate: " + str(poke_row['capture_rate']) + "%" + "\n"

    text += "╠════════════════════════════════════════════════╣\n"

    text += "║ BATTLE POWER (Total: " + str(poke_row['base_total']) + "):\n"
    text += "║ Health: " + str(poke_row['hp']) + "  Attack: " + str(poke_row['attack']) + "  Defense: " + str(poke_row['defense']) + "\n"
    text += "║ Sp. Atk: " + str(poke_row['sp_attack']) + "  Sp. Def: " + str(poke_row['sp_defense']) + "  Speed: " + str(poke_row['speed']) + "\n"

    text += "╠════════════════════════════════════════════════╣\n"
    text += "║ TOP MOVES:\n"

    for index, move_row in moves_list.iterrows():
        move_name = str(move_row['name'])
        move_power = str(move_row['power'])
        move_text = move_name + " (" + move_power + ")"
        if pd.notna(move_row['accuracy']):
            move_text += ", " + str(move_row['accuracy']) + "%"
        line = "║ " + move_text
        text += line + "\n"

    text += "╚════════════════════════════════════════════════╝"
    return text

# Its at this point in the code where I begin to implement Tkinter. 

def update_pokemon_display(text_widget, pokemon_df, moves_df, search_text, label_widget):
    """
    Updates the text box with the data of the pokemon when a valid Pokemon is found
    Also updates the selection label to show the currently selected Pokemon
    """
    pokemon_row = find_pokemon_by_name(pokemon_df, search_text)
    if pokemon_row is not None:
        display_text = create_pokemon_display_text(pokemon_row, moves_df)

        # Documentation for text widgets:
        # https://tkdocs.com/shipman/text.html
        # https://tkdocs.com/shipman/label.html
        text_widget.delete(1.0, tk.END)
        text_widget.insert(1.0, display_text)
        label_text = label_widget.cget("text").split(":")[0] + ": " + pokemon_row['name'].title()
        label_widget.config(text=label_text)

# Look at this function for the button documentation
def create_gold_button(parent, button_text, button_command):
    """
    Makes the buttons of the game
    """
    # Documentation for buttons that I used:
    # https://docs.python.org/3/library/tkinter.html#button-widgets
    # https://www.tcl-lang.org/man/tcl8.6/TkCmd/ttk_button.htm
    button = tk.Button(
        parent,
        text=button_text,
        font=('Arial', 14, 'bold'),
        bg='#ffeb3b',
        fg='#1a1a2e',
        relief=tk.RAISED,
        bd=8,
        padx=20,
        pady=15,
        cursor='hand2',
        command=button_command
    )
    return button

def update_hp_bars(battle, player_hp_bar, enemy_hp_bar, player_hp_label, enemy_hp_label, player_name, enemy_name):
    """
    Updates the canvas HP bars and labels for both pokemon
    """
    # Clamps HP to a valid range to handle overkill damage so HP only goes down until 0
    battle["player_hp"] = max(0, min(battle["player_hp"], battle["player_max_hp"]))
    battle["enemy_hp"] = max(0, min(battle["enemy_hp"], battle["enemy_max_hp"]))
    
    # Player HP bar: Calculates ratio and draws the green rectangle in the player's bar
    if battle["player_max_hp"] > 0:
        player_ratio = battle["player_hp"] / battle["player_max_hp"]
    else:
        player_ratio = 0
    player_hp_bar.delete("all")
    player_hp_bar.create_rectangle(0, 0, 300 * player_ratio, 25, fill='green', outline='white')
    player_hp_label.config(text=f"{player_name}  HP: {int(battle['player_hp'])}/{int(battle['player_max_hp'])}")

    # Enemy HP bar: Calculates ratio and the draws green rectangle in the enemy's bar
    if battle["enemy_max_hp"] > 0:
        enemy_ratio = battle["enemy_hp"] / battle["enemy_max_hp"]
    else:
        enemy_ratio = 0
    enemy_hp_bar.delete("all")
    enemy_hp_bar.create_rectangle(0, 0, 300 * enemy_ratio, 25, fill='green', outline='white')
    enemy_hp_label.config(text=f"{enemy_name}  HP: {int(battle['enemy_hp'])}/{int(battle['enemy_max_hp'])}")
    # I cite the documentation used for the bars in the create_battle_window() function because that's where these tkinter elements are created

def log_to_widget(battle, log_widget):
    """
    Updates the battle log with the current battle log entries
    """
    log_widget.config(state='normal') # Allows it to be altered
    log_widget.delete(1.0, tk.END) # Clears everything
    log_widget.insert(tk.END, "\n".join(battle["log"])) # Inserts the current battle log lines
    log_widget.config(state='disabled') # Disables the altering

def perform_attack(battle, attacker_poke, defender_poke, move_row, is_player_turn,log_widget, player_hp_bar, enemy_hp_bar, player_hp_label, enemy_hp_label):
    """
    Performs the attack move with accuracy, damage, and detection of win/loss
    """
    # Exit if battle already ended
    if battle["player_hp"] <= 0 or battle["enemy_hp"] <= 0:
        return False

    # Properties of the move
    move_name = str(move_row['name'])
    move_power = move_row['power']
    move_type = move_row['type']
    if 'accuracy' in move_row and not pd.isna(move_row['accuracy']):
        move_accuracy = move_row['accuracy']
    else:
        move_accuracy = 100

    # Accuracy check, handles miss case
    roll = random.uniform(0, 100)
    if roll > move_accuracy:
        if is_player_turn:
            text_line = f"Your {attacker_poke['name'].title()} used {move_name}, but it missed!"
        else:
            text_line = f"Enemy {attacker_poke['name'].title()} used {move_name}, but it missed!"
        battle["log"].append(text_line)
        log_to_widget(battle, log_widget)

        if is_player_turn:
            player_display_name = attacker_poke['name'].title()
            enemy_display_name = defender_poke['name'].title()
        else:
            player_display_name = defender_poke['name'].title()
            enemy_display_name = attacker_poke['name'].title()
        
        update_hp_bars(battle, player_hp_bar, enemy_hp_bar, player_hp_label, enemy_hp_label, player_display_name, enemy_display_name)
        return True

    # Calculates and applies damage
    damage = calculate_damage(attacker_poke, defender_poke, move_power, move_type, attacker_poke['type1'])
    
    if is_player_turn:
        battle["enemy_hp"] -= damage
        text_line = f"Your {attacker_poke['name'].title()} used {move_name}! It dealt {damage} damage."
    else:
        battle["player_hp"] -= damage
        text_line = f"Enemy {attacker_poke['name'].title()} used {move_name}! It dealt {damage} damage."

    battle["log"].append(text_line)

    # Win/loss detection and updates the battle log file
    if battle["enemy_hp"] <= 0 and is_player_turn:
        battle["log"].append(f"{defender_poke['name'].title()} fainted. You win!")
        full_battle_log.append("=== NEW BATTLE ===")
        full_battle_log.extend(battle["log"])
        write_battle_log()
    elif battle["player_hp"] <= 0 and not is_player_turn:
        battle["log"].append(f"{defender_poke['name'].title()} fainted. You lose!")
        full_battle_log.append("=== NEW BATTLE ===")
        full_battle_log.extend(battle["log"])
        write_battle_log()

    # Final UI refresh
    log_to_widget(battle, log_widget)
    # Determine display names based on turn order
    if is_player_turn:
        player_display_name = attacker_poke['name'].title()
        enemy_display_name = defender_poke['name'].title()
    else:
        player_display_name = defender_poke['name'].title()
        enemy_display_name = attacker_poke['name'].title()
    
    update_hp_bars(battle, player_hp_bar, enemy_hp_bar, player_hp_label, enemy_hp_label, player_display_name, enemy_display_name)
    return True

# Cites documentation for common tkinter features
def create_battle_window(player_poke, enemy_poke):
    """
    Creates:
        the whole battle UI as a popup window
        the HP bars and labels for the Pokemon
        the battle log
        the move buttons that the player's Pokemon can use

    Documentation for:
        Canvas and label widgets that I used:
            https://tkdocs.com/shipman/canvas.html
            https://tkdocs.com/shipman/label.html
            https://docs.python.org/3/library/tkinter.html#the-canvas-widget 
            https://www.tcl-lang.org/man/tcl8.6/TkCmd/canvas.htm (This is the best one, most detailed) 
        Windows and frames:
            https://www.geeksforgeeks.org/python/python-tkinter-toplevel-widget/ (This one documents how to just open a window)
            https://www.tcl-lang.org/man/tcl8.6/TkCmd/frame.htm (This one provides more details about the different properties and arguments)
            https://www.tcl-lang.org/man/tcl8.6/TkCmd/pack.htm#M5 (Packing)
        ScrolledText:
            A module for a scroll-bar for the battle log
            https://www.geeksforgeeks.org/python/python-tkinter-scrolledtext-widget/
        
    """
  
    global moves_df_global
    window = tk.Toplevel()
    window.title("Pokemon Battle")
    window.geometry("900x600")
    window.configure(bg='#1a1a2e')
    arena = tk.Frame(window, bg='#1a1a2e')
    arena.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)

    top_frame = tk.Frame(arena, bg='#1a1a2e')
    top_frame.pack(fill=tk.X, pady=(0, 20))

    player_side = tk.Frame(top_frame, bg='#1a1a2e')
    player_side.pack(side=tk.LEFT, padx=20)

    player_name_label = tk.Label(player_side, text=player_poke['name'].title(), font=('Arial', 16, 'bold'), bg='#1a1a2e', fg='#00ff88')
    player_name_label.pack(anchor='w')

    player_hp_label = tk.Label(player_side, text="", font=('Arial', 12), bg='#1a1a2e', fg='#ffffff')
    player_hp_label.pack(anchor='w', pady=(5, 2))

    player_hp_bar = tk.Canvas(player_side, width=300, height=25, bg='#550000', highlightthickness=1, highlightbackground='white')
    player_hp_bar.pack(anchor='w')

    enemy_side = tk.Frame(top_frame, bg='#1a1a2e')
    enemy_side.pack(side=tk.RIGHT, padx=20)

    enemy_name_label = tk.Label(enemy_side, text=enemy_poke['name'].title(), font=('Arial', 16, 'bold'), bg='#1a1a2e', fg='#ff4444')
    enemy_name_label.pack(anchor='e')

    enemy_hp_label = tk.Label(enemy_side, text="", font=('Arial', 12), bg='#1a1a2e', fg='#ffffff')
    enemy_hp_label.pack(anchor='e', pady=(5, 2))

    enemy_hp_bar = tk.Canvas(enemy_side, width=300, height=25, bg='#550000', highlightthickness=1, highlightbackground='white')
    enemy_hp_bar.pack(anchor='e')

    log_frame = tk.Frame(arena, bg='#1a1a2e')
    log_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 20))

    log_text = scrolledtext.ScrolledText(log_frame, height=8, wrap=tk.WORD, font=('Consolas', 11), bg='#0a0a0a', fg='#ffffff', insertbackground='#ffffff', state='disabled')
    log_text.pack(fill=tk.BOTH, expand=True)

    moves_frame = tk.Frame(arena, bg='#1a1a2e')
    moves_frame.pack(fill=tk.X)

    # Sets up the battle state
    player_hp_val = int(player_poke['hp']) * 2
    enemy_hp_val = int(enemy_poke['hp']) * 2

    battle = {
        "log": [],
        "player_max_hp": player_hp_val,
        "enemy_max_hp": enemy_hp_val,
        "player_hp": player_hp_val,
        "enemy_hp": enemy_hp_val
    }

    update_hp_bars(battle, player_hp_bar, enemy_hp_bar, player_hp_label, enemy_hp_label, player_poke['name'].title(), enemy_poke['name'].title())

    # Generates the moves for the player's Pokemon
    player_moves = get_level_proportional_moves(player_poke, moves_df_global)
    if len(player_moves) == 0:
        placeholder = tk.Label(moves_frame, text="No moves available for this Pokemon.", font=('Arial', 12), bg='#1a1a2e', fg='#ffffff')
        placeholder.pack()
        return

    # Generates the moves for the enemy's Pokemon
    enemy_moves = get_level_proportional_moves(enemy_poke, moves_df_global)
    if len(enemy_moves) == 0:
        enemy_moves = moves_df_global.sample(4)

    def enemy_turn():
        """
        Handles logic for the enemy Pokemon's turn
        """
        if battle["player_hp"] <= 0 or battle["enemy_hp"] <= 0:
            for btn in move_buttons: btn.config(state='disabled')
            return
        
        # Kept the logic basic by using .sample() for a random move
        move_row = enemy_moves.sample(1).iloc[0]
        perform_attack(battle, enemy_poke, player_poke, move_row, False, log_text, player_hp_bar, enemy_hp_bar, player_hp_label, enemy_hp_label)
        if battle["player_hp"] <= 0:
            for btn in move_buttons: btn.config(state='disabled')

    def player_move_clicked(index):
        """
        Handles logic for the player's Pokemon move that it selects
        """
        if battle["player_hp"] <= 0 or battle["enemy_hp"] <= 0: return
        move_row = player_moves.iloc[index]
        perform_attack(battle, player_poke, enemy_poke, move_row, True, log_text, player_hp_bar, enemy_hp_bar, player_hp_label, enemy_hp_label)
        if battle["enemy_hp"] <= 0:
            for btn in move_buttons: btn.config(state='disabled')
            return
        enemy_turn()

    move_buttons = []
    for i in range(len(player_moves)):
        move = player_moves.iloc[i]
        btn_text = f"{move['name']} ({int(move['power']) if not pd.isna(move['power']) else 0})"
        btn = tk.Button(moves_frame, text=btn_text, font=('Arial', 12, 'bold'), bg='#ffeb3b', fg='#1a1a2e', relief=tk.RAISED, bd=4, padx=10, pady=10, cursor='hand2', command=lambda idx=i: player_move_clicked(idx))
        btn.pack(side=tk.LEFT, padx=10, pady=5)
        move_buttons.append(btn)

    end_btn = tk.Button(moves_frame, text="End Match", font=('Arial', 12, 'bold'), bg='#ffeb3b', fg='#1a1a2e', relief=tk.RAISED, bd=4, padx=10, pady=10, cursor='hand2', command=window.destroy)
    end_btn.pack(side=tk.RIGHT, padx=10, pady=5)

def create_main_window():
    """
    Creates the main app window with the Pokemon selecting UI
    Left panel for Player pokemon search/display/selection
    Right panel for Enenmy pokemon search/display/selection

    Documentation for:
        global keyword:
            https://realpython.com/ref/keywords/global/ (I feel this one did a better job explaining it than geeksforgeeks.org)
        
    """
    global moves_df_global

    # Opens the main window with the same logic as create_battle_window(), but it's called root instead of window
    root = tk.Tk()
    root.title("PokeSim - V1")
    root.geometry("1400x800")
    root.configure(bg='#1a1a2e')

    player_pokemon = [None] # Setting it to None because an empty list would have no index 0
    enemy_pokemon = [None]

    pokemon_df = load_pokemon_data()
    moves_df_global = load_moves_data()

    main_container = tk.Frame(root, bg='#1a1a2e')
    main_container.pack(fill=tk.BOTH, expand=True, padx=30, pady=30)

    header = tk.Frame(main_container, bg='#16213e', relief=tk.RAISED, bd=3)
    header.pack(fill=tk.X, pady=(0, 20))
    title = tk.Label(header, text="POKEMON BATTLE SELECTOR", font=('Arial', 24, 'bold'), bg='#16213e', fg='#00d4ff')
    title.pack(pady=15)

    subtitle = tk.Label(header, text="Choose your Pokemon (left) and AI opponent (right)", font=('Arial', 12), bg='#16213e', fg='#ffffff') # Not really AI, but calling it that just made the game seem less dull
    subtitle.pack(pady=(0, 15))

    content = tk.Frame(main_container, bg='#1a1a2e')
    content.pack(fill=tk.BOTH, expand=True)

    left_panel = tk.Frame(content, bg='#1a1a2e')
    left_panel.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 15))

    player_search_box = tk.Frame(left_panel, bg='#0f3460', relief=tk.RAISED, bd=3)
    player_search_box.pack(fill=tk.X, pady=(0, 10))

    player_title = tk.Label(player_search_box, text="YOUR POKEMON", font=('Arial', 16, 'bold'), bg='#0f3460', fg='#00ff88')
    player_title.pack(pady=15)

    # StringVar() holds string variables in tkinter
    player_search_var = tk.StringVar()
    player_entry = tk.Entry(player_search_box, textvariable=player_search_var, font=('Arial', 16), width=35, relief=tk.FLAT, bg='#ffffff', fg='#333333', insertbackground='#00ff88')
    player_entry.pack(pady=15)

    player_display_box = tk.Frame(left_panel, bg='#0f4d40', relief=tk.RAISED, bd=3)
    player_display_box.pack(fill=tk.BOTH, expand=True)

    player_display_title = tk.Label(player_display_box, text="YOUR POKEMON INFO", font=('Arial', 14, 'bold'), bg='#0f4d40', fg='#00ff88')
    player_display_title.pack(pady=10)

    # Creates a scrollable text box, later realized it was unnecessary since the data isn't very long but it doesn't make any difference if I revert to a regular box
    player_text = scrolledtext.ScrolledText(player_display_box, height=22, wrap=tk.WORD, font=('Consolas', 11), bg='#0a1f1a', fg='#ffffff', insertbackground='#00ff88')
    player_text.pack(fill=tk.BOTH, expand=True, padx=15, pady=(0, 10))

    player_button_box = tk.Frame(player_display_box, bg='#0f4d40')
    player_button_box.pack(fill=tk.X, padx=15, pady=(0, 10))

    player_current_label = tk.Label(player_button_box, text="Your Pokemon: None", font=('Arial', 11), bg='#0f4d40', fg='#ffd700')
    player_current_label.pack(pady=8)

    right_panel = tk.Frame(content, bg='#1a1a2e')
    right_panel.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=(15, 0))

    enemy_search_box = tk.Frame(right_panel, bg='#8b0000', relief=tk.RAISED, bd=3)
    enemy_search_box.pack(fill=tk.X, pady=(0, 10))

    enemy_title = tk.Label(enemy_search_box, text="AI OPPONENT", font=('Arial', 16, 'bold'), bg='#8b0000', fg='#ff4444')
    enemy_title.pack(pady=15)

    enemy_search_var = tk.StringVar()
    enemy_entry = tk.Entry(enemy_search_box, textvariable=enemy_search_var, font=('Arial', 16), width=35, relief=tk.FLAT, bg='#ffffff', fg='#333333', insertbackground='#ff4444')
    enemy_entry.pack(pady=15)

    enemy_display_box = tk.Frame(right_panel, bg='#660000', relief=tk.RAISED, bd=3)
    enemy_display_box.pack(fill=tk.BOTH, expand=True)

    enemy_display_title = tk.Label(enemy_display_box, text="OPPONENT INFO", font=('Arial', 14, 'bold'), bg='#660000', fg='#ff4444')
    enemy_display_title.pack(pady=10)

    enemy_text = scrolledtext.ScrolledText(enemy_display_box, height=22, wrap=tk.WORD, font=('Consolas', 11), bg='#2a0000', fg='#ffffff', insertbackground='#ff4444')
    enemy_text.pack(fill=tk.BOTH, expand=True, padx=15, pady=(0, 10))

    enemy_button_box = tk.Frame(enemy_display_box, bg='#660000')
    enemy_button_box.pack(fill=tk.X, padx=15, pady=(0, 10))

    enemy_current_label = tk.Label(enemy_button_box, text="Opponent: None", font=('Arial', 11), bg='#660000', fg='#ffd700')
    enemy_current_label.pack(pady=8)

    battle_button_box = tk.Frame(main_container, bg='#1a1a2e')
    battle_button_box.pack(fill=tk.X, pady=20)

    def enemy_random_function():
        """
        Picks a random Pokemon as the AI opponent and updates the display/label.
        """
        random_row = pokemon_df.sample(1).iloc[0]
        enemy_pokemon[0] = random_row

        # Update the info box text
        display_text = create_pokemon_display_text(random_row, moves_df_global)
        enemy_text.delete(1.0, tk.END)
        enemy_text.insert(1.0, display_text)

        # Update the label
        enemy_current_label.config(text="Opponent: " + random_row['name'].title(), fg='#ffaa00'
        )


    def start_battle_function(player, enemy, df, battle_func):
        """
        Starts the battle if both sides have selected a Pokemon
        """
        if player[0] is not None and enemy[0] is not None: 
            battle_func(player[0], enemy[0])
        else: 
            # Displays a warning if one of the sides doesn't have a selected Pokemon
            messagebox.showwarning("Missing Pokemon", "Select both Pokemon first!")

    start_battle_btn = create_gold_button(battle_button_box, "START BATTLE", lambda: start_battle_function(player_pokemon, enemy_pokemon, pokemon_df, create_battle_window))
    start_battle_btn.pack()

    # The event=None parameter allows these functions to handle two different calling scenarios:
    #   1) Event-driven calls (player_entry.bind) - Tkinter automatically passes an Event object
    #   2) Regular, manual calls (player_search_function()) - No event object exists, so event=None provides a default value
    def player_search_function(event=None):
        """
        Handles the Pokemon search feature for the player's Pokemon
        Has live search so it checks every time if the player typed an existing Pokemon
        """
        search_value = player_search_var.get().strip()
        update_pokemon_display(player_text, pokemon_df, moves_df_global, search_value, player_current_label)

        if search_value: # Is the search text NOT empty?
            found_poke = find_pokemon_by_name(pokemon_df, search_value)
            if found_poke is not None: # Was a Pokemon found?
                player_pokemon[0] = found_poke

    def player_select_function():
        """
        Confirms the player's Pokemon selection and updates the label
        """
        if player_pokemon[0] is not None: 
            player_current_label.config(text="Your Pokemon: " + player_pokemon[0]['name'].title(), fg='#00ff88')

    def enemy_search_function(event=None):
        """
        Handles the Pokemon search feature for the enemy's Pokemon
        Has live search so it checks every time if the player typed an existing Pokemon
        """
        search_value = enemy_search_var.get().strip()
        update_pokemon_display(enemy_text, pokemon_df, moves_df_global, search_value, enemy_current_label)

        if search_value:
            found_poke = find_pokemon_by_name(pokemon_df, search_value)
            if found_poke is not None: 
                enemy_pokemon[0] = found_poke

    def enemy_select_function():
        """
        Confirms the enemy's Pokemon selection and updates the label
        """
        if enemy_pokemon[0] is not None: 
            enemy_current_label.config(text="Opponent: " + enemy_pokemon[0]['name'].title(), fg='#ffaa00')

    player_entry.bind('<KeyRelease>', player_search_function)
    player_entry.bind('<Return>', player_search_function)

    enemy_entry.bind('<KeyRelease>', enemy_search_function)
    enemy_entry.bind('<Return>', enemy_search_function)

    player_select_btn = create_gold_button(player_button_box, "SELECT AS YOUR POKEMON", player_select_function)
    player_select_btn.pack()

    enemy_select_btn = create_gold_button(enemy_button_box, "SELECT AS AI OPPONENT", enemy_select_function)
    enemy_select_btn.pack(side=tk.LEFT, padx=30, pady=5)

    enemy_random_btn = create_gold_button(enemy_button_box, "CHOOSE RANDOM OPPONENT", enemy_random_function)
    enemy_random_btn.pack(side=tk.LEFT, padx=40, pady=5)



    # This is the infinite loop that keeps the window alive until its closed
    root.mainloop()

def test_battle():
    """
    This is the test method that runs unit tests to make sure the core battle mechanics are working correctly
    Provides immediate feedback when a test fails
    """
    try:
        pokemon_df = load_pokemon_data()
        moves_df = load_moves_data()

        # Verify that the CSV files load
        assert len(pokemon_df) > 0, "pokemon.csv is empty"
        assert len(moves_df) > 0, "moves.csv is empty"

        # Verify that Pokemon lookup works for common Pokemon
        pikachu = find_pokemon_by_name(pokemon_df, "pikachu")
        squirtle = find_pokemon_by_name(pokemon_df, "SqUirTLe") # Checking to see if case doesn't matter
        assert pikachu is not None, "Pikachu not found in pokemon.csv"
        assert squirtle is not None, "Squirtle not found in pokemon.csv"

        # Verify that single damage calculations produce realistic values
        dmg = calculate_damage(pikachu, squirtle, 40, "electric", "electric")
        assert 10 <= dmg <= 80, f"Damage out of expected range: {dmg}"
        print("TEST 1 PASSED: Pikachu vs Squirtle damage:", dmg)

        # Verify that damage always produces positive values (no zero damage)
        damages = [calculate_damage(pikachu, squirtle, 40, "electric", "electric") for i in range(5)]
        assert all(d > 0 for d in damages), f"Some damages are non-positive: {damages}"
        print("TEST 2 PASSED: Multiple damage values:", damages)

        # Verify that the STAB (Same-Type Attack Bonus) increases electric damage vs normal
        electric_dmg = calculate_damage(pikachu, squirtle, 40, "electric", "electric")
        normal_dmg = calculate_damage(pikachu, squirtle, 40, "normal", "electric")
        assert electric_dmg > normal_dmg, f"STAB failed: electric={electric_dmg} not > normal={normal_dmg}"
        print("TEST 3 PASSED: Electric dmg =", electric_dmg, "Normal dmg =", normal_dmg)

        # Verify that the move selection returns correct number of moves (1-4)
        pika_moves = get_level_proportional_moves(pikachu, moves_df)
        assert 1 <= len(pika_moves) <= 4, f"Pikachu move count invalid: {len(pika_moves)}"
        print("TEST 4 PASSED: Pikachu moves:", list(pika_moves['name']))

        # Verify that the type chart multipliers work correctly
        mult_electric_water = get_type_multiplier("electric", "water")
        mult_normal_rock = get_type_multiplier("normal", "rock")
        assert mult_electric_water > 1.0, "Electric vs Water multiplier should be > 1"
        assert mult_normal_rock < 1.0, "Normal vs Rock multiplier should be < 1"
        print("TEST 5 PASSED: Type multipliers behave as expected.")

        print("All tests in test_battle() completed.")

    except AssertionError as e:
        print("TEST FAILED:", e)

if __name__ == "__main__":
    test_battle()
    create_main_window()
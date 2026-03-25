# test_state.py
from game_state import initialize_game

game = initialize_game()
print(f"Players: {len(game.players)}")
print(f"Crewmates: {len(game.get_crewmates())}")
print(f"Impostors: {len(game.get_impostors())}")
print(f"Initial phase: {game.phase}")
print(f"Victory condition: {game.check_victory()}")
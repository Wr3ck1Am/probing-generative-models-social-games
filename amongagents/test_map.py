from game_map import get_adjacent_rooms, is_adjacent

print("Cafeteria adjacent rooms:", get_adjacent_rooms("Cafeteria"))
print("Can move Cafeteria -> Weapons?", is_adjacent("Cafeteria", "Weapons"))
print("Can move Cafeteria -> Reactor?", is_adjacent("Cafeteria", "Reactor"))
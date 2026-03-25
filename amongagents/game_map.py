"""
Among Us 14房间地图拓扑
"""

from dataclasses import dataclass
from typing import List, Dict

@dataclass
class Room:
    name: str
    connections: List[str]
    
# 房间连接关系
ROOM_CONNECTIONS = {
    "Cafeteria": ["Weapons", "Upper Engine", "MedBay", "Admin"],
    "Weapons": ["Cafeteria", "O2", "Navigation"],
    "O2": ["Weapons", "Navigation", "Shields"],
    "Navigation": ["Weapons", "O2", "Shields"],
    "Shields": ["O2", "Navigation", "Storage", "Communications"],
    "Communications": ["Shields", "Storage"],
    "Storage": ["Shields", "Communications", "Electrical", "Admin"],
    "Electrical": ["Storage", "Lower Engine"],
    "Lower Engine": ["Electrical", "Security", "Reactor"],
    "Security": ["Lower Engine", "Reactor", "Upper Engine"],
    "Reactor": ["Lower Engine", "Security", "Upper Engine"],
    "Upper Engine": ["Cafeteria", "Reactor", "Security", "MedBay"],
    "MedBay": ["Cafeteria", "Upper Engine"],
    "Admin": ["Cafeteria", "Storage"],
}

# 房间任务
ROOM_TASKS = {
    "Cafeteria": ["Empty Garbage", "Fix Wiring"],
    "Weapons": ["Clear Asteroids", "Download Data"],
    "O2": ["Clean O2 Filter", "Fix Wiring"],
    "Navigation": ["Chart Course", "Download Data"],
    "Shields": ["Prime Shields", "Fix Wiring"],
    "Communications": ["Download Data"],
    "Storage": ["Fuel Engines", "Empty Garbage"],
    "Electrical": ["Fix Wiring", "Calibrate Distributor", "Download Data"],
    "Lower Engine": ["Fuel Engines", "Align Engine Output"],
    "Security": ["Fix Wiring"],
    "Reactor": ["Unlock Manifolds", "Start Reactor"],
    "Upper Engine": ["Fuel Engines", "Align Engine Output"],
    "MedBay": ["Submit Scan", "Inspect Sample"],
    "Admin": ["Swipe Card", "Upload Data"],
}

def get_adjacent_rooms(room_name: str) -> List[str]:
    return ROOM_CONNECTIONS.get(room_name, [])

def get_room_tasks(room_name: str) -> List[str]:
    return ROOM_TASKS.get(room_name, [])

def is_adjacent(room1: str, room2: str) -> bool:
    return room2 in ROOM_CONNECTIONS.get(room1, [])
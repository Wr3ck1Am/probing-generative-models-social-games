"""
Core game state definitions and initialization.
"""

from dataclasses import dataclass, field
from typing import List, Dict, Optional, Literal
from enum import Enum
import random

class Phase(Enum):
    TASK = "task"
    MEETING = "meeting"

class Role(Enum):
    CREWMATE = "crewmate"
    IMPOSTOR = "impostor"

# Neutral player names (so roles are not leaked)
PLAYER_NAMES = ["Alice", "Bob", "Charlie", "Diana", "Evan"]

@dataclass
class MeetingState:
    """Tracks discussion history and votes during a meeting."""
    discussion_history: List[Dict] = field(default_factory=list)
    votes: Dict[int, str] = field(default_factory=dict)
    current_round: int = 0
    trigger_reason: str = "scheduled"  # "scheduled" or "body_found"
    body_found_by: Optional[str] = None
    body_location: Optional[str] = None

    def add_speech(self, player_name: str, message: str):
        self.discussion_history.append({"player": player_name, "message": message})

    def get_formatted_history(self) -> str:
        if not self.discussion_history:
            return "No one has spoken yet."
        return "\n".join([
            f"{entry['player']}: {entry['message']}"
            for entry in self.discussion_history[-10:]
        ])

@dataclass
class Task:
    name: str
    location: str
    task_type: Literal["short", "long", "common"]
    steps_remaining: int = 1
    completed: bool = False

@dataclass
class Player:
    id: int
    name: str
    role: Role
    personality: str
    location: str
    alive: bool = True
    tasks: List[Task] = field(default_factory=list)
    observation_history: List[str] = field(default_factory=list)
    action_history: List[str] = field(default_factory=list)

@dataclass
class GameState:
    phase: Phase
    timestep: int
    max_timesteps: int
    players: List[Player]
    meeting_state: Optional[MeetingState] = None
    dead_bodies: List[Dict] = field(default_factory=list)  # [{"player_id": int, "location": str}]
    kill_log: List[Dict] = field(default_factory=list)  # track all kills

    def get_alive_players(self) -> List[Player]:
        return [p for p in self.players if p.alive]

    def get_crewmates(self) -> List[Player]:
        return [p for p in self.players if p.role == Role.CREWMATE]

    def get_impostors(self) -> List[Player]:
        return [p for p in self.players if p.role == Role.IMPOSTOR]

    def get_player_by_name(self, name: str) -> Optional['Player']:
        for p in self.players:
            if p.name == name:
                return p
        return None

    def check_victory(self) -> Optional[str]:
        alive = self.get_alive_players()
        alive_crew = [p for p in alive if p.role == Role.CREWMATE]
        alive_imp = [p for p in alive if p.role == Role.IMPOSTOR]

        if len(alive_imp) == 0:
            return "crewmate"
        if len(alive_crew) <= len(alive_imp):
            return "impostor"
        if self.timestep >= self.max_timesteps:
            return "impostor"

        all_crew_tasks = [task for p in self.get_crewmates() for task in p.tasks]
        if all_crew_tasks and all(t.completed for t in all_crew_tasks):
            return "crewmate"

        return None

def initialize_game(num_crewmates: int = 4, num_impostors: int = 1,
                    personalities: Optional[Dict[str, str]] = None) -> GameState:
    """Set up a new game with the given player counts and personalities."""
    total = num_crewmates + num_impostors
    names = PLAYER_NAMES[:total]
    random.shuffle(names)

    # Randomly pick impostor indices
    indices = list(range(total))
    impostor_indices = set(random.sample(indices, num_impostors))

    players = []
    for i in range(total):
        role = Role.IMPOSTOR if i in impostor_indices else Role.CREWMATE
        name = names[i]
        personality = (personalities or {}).get(name, "default")

        if role == Role.CREWMATE:
            tasks = [
                Task(name="Fix Wiring", location="Electrical", task_type="common", steps_remaining=1),
                Task(name="Download Data", location="Admin", task_type="short", steps_remaining=1),
                Task(name="Clear Asteroids", location="Weapons", task_type="long", steps_remaining=2),
            ]
        else:
            tasks = [
                Task(name="Fix Wiring", location="Electrical", task_type="common", steps_remaining=1),
            ]

        player = Player(
            id=i,
            name=name,
            role=role,
            personality=personality,
            location="Cafeteria",
            tasks=tasks
        )
        players.append(player)

    return GameState(
        phase=Phase.TASK,
        timestep=0,
        max_timesteps=20,
        players=players
    )

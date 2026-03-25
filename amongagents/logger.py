"""
游戏日志系统 - JSON格式
"""

import json
import os
from datetime import datetime
from typing import Dict, List, Optional


class GameLogger:
    def __init__(self, config_name: str, run_id: int, log_dir: str = "logs"):
        self.config_name = config_name
        self.run_id = run_id
        self.log_dir = log_dir
        os.makedirs(log_dir, exist_ok=True)

        self.start_time = datetime.now().isoformat()
        self.meta = {}
        self.players_info = []
        self.turns = []
        self.meetings = []
        self.outcome = {}
        self.total_input_tokens = 0
        self.total_output_tokens = 0
        self.total_api_calls = 0

    def set_meta(self, config, players):
        self.meta = {
            "game_id": f"{self.config_name}_{self.run_id:03d}",
            "config": self.config_name,
            "run_id": self.run_id,
            "timestamp_start": self.start_time,
            "model": config.model,
            "memory_size": config.memory_size,
            "planning_enabled": config.planning_enabled,
            "crew_agent_type": config.crew_agent_type,
            "impostor_agent_type": config.impostor_agent_type,
        }
        self.players_info = [
            {
                "id": p.id,
                "name": p.name,
                "role": p.role.value,
                "personality": p.personality,
                "tasks_assigned": [f"{t.name}@{t.location}" for t in p.tasks],
            }
            for p in players
        ]

    def log_turn(self, timestep: int, phase: str, player_actions: List[Dict]):
        self.turns.append({
            "timestep": timestep,
            "phase": phase,
            "player_actions": player_actions,
        })

    def log_action(self, player, observation: str, action: Dict,
                   result: Dict, metadata: Optional[Dict] = None):
        """记录一个玩家的行动"""
        entry = {
            "player_id": player.id,
            "player_name": player.name,
            "location": player.location,
            "observation_text": observation[:500],  # truncate for log size
            "action": action,
            "action_result": result,
        }
        if metadata:
            entry["thought"] = metadata.get("thought", "")
            entry["plan"] = metadata.get("plan", "")
            if "input_tokens" in metadata:
                self.total_input_tokens += metadata["input_tokens"]
                self.total_output_tokens += metadata.get("output_tokens", 0)
                self.total_api_calls += 1
                entry["api_usage"] = {
                    "input_tokens": metadata["input_tokens"],
                    "output_tokens": metadata.get("output_tokens", 0),
                }
        return entry

    def log_meeting(self, timestep: int, trigger_reason: str,
                    discussion_rounds: List[List[Dict]],
                    votes: Dict, vote_result: Dict,
                    body_info: Optional[Dict] = None):
        meeting = {
            "triggered_at_timestep": timestep,
            "trigger_reason": trigger_reason,
            "body_info": body_info,
            "discussion_rounds": discussion_rounds,
            "votes": votes,
            "vote_result": vote_result,
        }
        self.meetings.append(meeting)

    def set_outcome(self, winner: str, reason: str, timesteps: int,
                    total_kills: int, total_meetings: int, tasks_completed: int):
        self.outcome = {
            "winner": winner,
            "reason": reason,
            "total_timesteps": timesteps,
            "total_kills": total_kills,
            "total_meetings": total_meetings,
            "tasks_completed": tasks_completed,
        }

    def finalize(self):
        self.meta["timestamp_end"] = datetime.now().isoformat()
        self.meta["total_api_calls"] = self.total_api_calls
        self.meta["total_input_tokens"] = self.total_input_tokens
        self.meta["total_output_tokens"] = self.total_output_tokens

        # Update player survival and task completion
        log_data = {
            "meta": self.meta,
            "players": self.players_info,
            "outcome": self.outcome,
            "turns": self.turns,
            "meetings": self.meetings,
        }

        filename = f"game_{self.config_name}_{self.run_id:03d}.json"
        filepath = os.path.join(self.log_dir, filename)
        with open(filepath, "w") as f:
            json.dump(log_data, f, indent=2, ensure_ascii=False)
        return filepath

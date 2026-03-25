"""
Random baseline agent for control experiments.
"""

import random
from typing import Dict, List
from game_state import Player, GameState, Phase, MeetingState
from game_map import get_adjacent_rooms


class RandomAgent:
    def __init__(self, player: Player):
        self.player = player

    def decide_action(self, game_state: GameState) -> tuple:
        """Pick a uniformly random legal action."""
        if game_state.phase == Phase.TASK:
            actions = self._get_task_actions(game_state)
        else:
            actions = self._get_meeting_actions(game_state)

        action = random.choice(actions) if actions else {"action": "idle", "params": {}}
        metadata = {"thought": "[random]", "plan": "[random]",
                    "input_tokens": 0, "output_tokens": 0}
        return action, metadata

    def decide_meeting_action(self, game_state: GameState,
                              meeting_state: MeetingState) -> tuple:
        if meeting_state.current_round < 2:
            # Discussion round - say something generic or stay silent
            messages = [
                "I don't have much to say.",
                "I was just doing my tasks.",
                "Anyone seen anything suspicious?",
                "I think we should skip this vote.",
            ]
            action = {"action": "speak", "params": {"message": random.choice(messages)}}
        else:
            # Voting round
            alive = [p.name for p in game_state.get_alive_players()
                     if p.id != self.player.id]
            targets = alive + ["skip"]
            action = {"action": "vote", "params": {"target": random.choice(targets)}}

        metadata = {"thought": "[random]", "plan": "[random]",
                    "input_tokens": 0, "output_tokens": 0}
        return action, metadata

    def _get_task_actions(self, game_state: GameState) -> List[Dict]:
        actions = []

        # Move to a random adjacent room
        adj = get_adjacent_rooms(self.player.location)
        for room in adj:
            actions.append({"action": "move", "params": {"target_room": room}})

        # Complete task if at task location
        if self.player.role.value == "crewmate":
            for task in self.player.tasks:
                if not task.completed and task.location == self.player.location:
                    actions.append({"action": "complete_task",
                                    "params": {"task_name": task.name}})

        # Kill if impostor and someone is in the same room
        if self.player.role.value == "impostor":
            same_room = [p for p in game_state.get_alive_players()
                         if p.location == self.player.location and p.id != self.player.id]
            for target in same_room:
                actions.append({"action": "kill",
                                "params": {"target_player": target.name}})

        return actions if actions else [{"action": "idle", "params": {}}]

    def _get_meeting_actions(self, game_state: GameState) -> List[Dict]:
        alive = [p.name for p in game_state.get_alive_players()
                 if p.id != self.player.id]
        targets = alive + ["skip"]
        return [{"action": "vote", "params": {"target": t}} for t in targets]

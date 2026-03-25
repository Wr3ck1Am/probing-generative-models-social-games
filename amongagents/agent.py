"""
LLM-powered Among Us player using OpenAI function calling.
"""

import json
from openai import OpenAI
from typing import List, Dict, Tuple
from game_state import Player, GameState, Phase, MeetingState
from game_map import get_adjacent_rooms
from config import ALL_PERSONALITIES


class AmongUsAgent:
    def __init__(self, player: Player, api_key: str,
                 model: str = "gpt-4o-mini",
                 memory_size: int = 10,
                 planning_enabled: bool = True):
        self.player = player
        self.client = OpenAI(api_key=api_key)
        self.model = model
        self.memory = []
        self.max_memory_items = memory_size
        self.planning_enabled = planning_enabled

    def add_to_memory(self, observation: str, action: Dict):
        if self.max_memory_items == 0:
            return
        self.memory.append({
            "observation": observation,
            "action": f"{action['action']}: {action['params']}"
        })
        if len(self.memory) > self.max_memory_items:
            self._compress_memory()

    def _compress_memory(self):
        old_memories = self.memory[:5]
        memory_text = "\n".join([
            f"T{i}: Saw {m['observation'][:50]}... -> Did {m['action']}"
            for i, m in enumerate(old_memories)
        ])
        response = self.client.chat.completions.create(
            model=self.model, max_completion_tokens=200,
            messages=[
                {"role": "system", "content": "Summarize game events concisely."},
                {"role": "user", "content": f"Summarize these game events in 2-3 sentences:\n{memory_text}"}
            ]
        )
        summary = response.choices[0].message.content or ""
        self.memory = [{"observation": "Summary", "action": summary}] + self.memory[5:]

    def get_memory_context(self) -> str:
        if not self.memory:
            return "No previous memory."
        recent = self.memory[-5:]
        start_index = max(0, len(self.memory) - len(recent))
        return "\n".join([
            f"Step {i}: {m['action']}"
            for i, m in enumerate(recent, start=start_index + 1)
        ])

    def _get_personality_prompt(self) -> str:
        key = self.player.personality
        if key and key != "default" and key in ALL_PERSONALITIES:
            return f"\n=== YOUR PERSONALITY ===\n{ALL_PERSONALITIES[key]}\n"
        return ""

    def get_observation(self, game_state: GameState) -> str:
        obs_parts = []
        obs_parts.append(f"Current Phase: {game_state.phase.value.upper()}")
        obs_parts.append(f"Timestep: {game_state.timestep}/{game_state.max_timesteps}")
        obs_parts.append(f"\nYour name: {self.player.name}")
        obs_parts.append(f"Your location: {self.player.location}")
        same_room = [p for p in game_state.get_alive_players()
                     if p.location == self.player.location and p.id != self.player.id]
        if same_room:
            obs_parts.append(f"Players in this room: {[p.name for p in same_room]}")
        else:
            obs_parts.append("You are alone in this room.")
        bodies_here = [b for b in game_state.dead_bodies if b["location"] == self.player.location]
        if bodies_here:
            body_names = [game_state.players[b["player_id"]].name for b in bodies_here]
            obs_parts.append(f"DEAD BODIES HERE: {body_names}")
        adjacent = get_adjacent_rooms(self.player.location)
        obs_parts.append(f"Adjacent rooms: {adjacent}")
        alive_names = [p.name for p in game_state.get_alive_players() if p.id != self.player.id]
        obs_parts.append(f"Alive players: {alive_names}")
        if self.player.role.value == "crewmate":
            incomplete = [f"{t.name} at {t.location}" for t in self.player.tasks if not t.completed]
            completed = [t.name for t in self.player.tasks if t.completed]
            obs_parts.append(f"\nYour remaining tasks: {incomplete}")
            if completed:
                obs_parts.append(f"Completed tasks: {completed}")
        return "\n".join(obs_parts)

    def _get_tools(self, game_state: GameState) -> List[Dict]:
        if game_state.phase == Phase.TASK:
            tools = [
                {"type": "function", "function": {"name": "move", "description": "Move to an adjacent room",
                    "parameters": {"type": "object", "properties": {"target_room": {"type": "string", "description": "Name of adjacent room"}}, "required": ["target_room"]}}},
                {"type": "function", "function": {"name": "speak", "description": "Say something to players in the same room",
                    "parameters": {"type": "object", "properties": {"message": {"type": "string"}}, "required": ["message"]}}},
            ]
            if self.player.role.value == "crewmate":
                tools.append({"type": "function", "function": {"name": "complete_task", "description": "Complete a task at your current location",
                    "parameters": {"type": "object", "properties": {"task_name": {"type": "string"}}, "required": ["task_name"]}}})
            if self.player.role.value == "impostor":
                tools.append({"type": "function", "function": {"name": "kill", "description": "Eliminate a player in the same room",
                    "parameters": {"type": "object", "properties": {"target_player": {"type": "string"}}, "required": ["target_player"]}}})
            return tools
        elif game_state.phase == Phase.MEETING:
            return [
                {"type": "function", "function": {"name": "speak", "description": "Speak during the meeting",
                    "parameters": {"type": "object", "properties": {"message": {"type": "string"}}, "required": ["message"]}}},
                {"type": "function", "function": {"name": "vote", "description": "Vote to eject a player or skip",
                    "parameters": {"type": "object", "properties": {"target": {"type": "string", "description": "Player name or 'skip'"}}, "required": ["target"]}}},
            ]
        return []

    def _parse_response(self, response) -> Tuple[Dict, Dict]:
        msg = response.choices[0].message
        text = msg.content or ""
        thought, plan = "", ""
        if "[THOUGHT]" in text:
            t = text.split("[THOUGHT]", 1)[1]
            thought = t.split("[PLAN]")[0].split("[ACTION]")[0].strip()[:300]
        if "[PLAN]" in text:
            p = text.split("[PLAN]", 1)[1]
            plan = p.split("[ACTION]")[0].strip()[:300]
        if not thought and text:
            thought = text[:300].strip()
        action = {"action": "idle", "params": {}}
        if msg.tool_calls:
            tc = msg.tool_calls[0]
            try:
                params = json.loads(tc.function.arguments)
            except (json.JSONDecodeError, TypeError):
                params = {}
            action = {"action": tc.function.name, "params": params}
        metadata = {
            "thought": thought, "plan": plan,
            "input_tokens": response.usage.prompt_tokens if response.usage else 0,
            "output_tokens": response.usage.completion_tokens if response.usage else 0,
        }
        return action, metadata

    def decide_action(self, game_state: GameState) -> Tuple[Dict, Dict]:
        observation = self.get_observation(game_state)
        tools = self._get_tools(game_state)
        personality_prompt = self._get_personality_prompt()
        system_prompt = f"""You are playing Among Us as a {self.player.role.value.upper()}.
Your name: {self.player.name}
Your role: {self.player.role.value}
{'Your goal: Complete all tasks and find the Impostor.' if self.player.role.value == 'crewmate' else 'Your goal: Eliminate Crewmates without being caught. Pretend to be a Crewmate.'}
{personality_prompt}
=== YOUR RECENT MEMORY ===
{self.get_memory_context()}

=== CURRENT SITUATION ===
{observation}

Think step by step and choose the best action. You MUST call one of the available functions."""
        if self.planning_enabled:
            user_content = """Analyze the situation and decide your action.

Format your response as:
[THOUGHT] What is my goal right now? What are my options?
[PLAN] What should I do next and why?
[ACTION] (Call the appropriate function)

Now, what do you want to do?"""
        else:
            user_content = "Choose your next action. Call a function."
        response = self.client.chat.completions.create(
            model=self.model, max_completion_tokens=1024,
            messages=[{"role": "system", "content": system_prompt}, {"role": "user", "content": user_content}],
            tools=tools, tool_choice="required",
        )
        action, metadata = self._parse_response(response)
        self.add_to_memory(observation, action)
        return action, metadata

    def decide_meeting_action(self, game_state: GameState, meeting_state: MeetingState) -> Tuple[Dict, Dict]:
        discussion_history = meeting_state.get_formatted_history()
        personality_prompt = self._get_personality_prompt()
        meeting_context = ""
        if meeting_state.trigger_reason == "body_found":
            meeting_context = f"\nThis meeting was called because {meeting_state.body_found_by} found a dead body in {meeting_state.body_location}!"
        system_prompt = f"""You are in an Among Us meeting to discuss who might be the Impostor.
Your name: {self.player.name}
Your role: {self.player.role.value}
{'You know you are innocent. Help find the real Impostor.' if self.player.role.value == 'crewmate' else 'You ARE the Impostor. Defend yourself and deflect suspicion onto others.'}
{personality_prompt}{meeting_context}

=== DISCUSSION SO FAR ===
{discussion_history}

=== YOUR RECENT MEMORY ===
{self.get_memory_context()}

Current round: {meeting_state.current_round + 1}/3
If this is a discussion round (1-2), use speak. If voting round (3), use vote.
You MUST call one of the available functions."""
        tools = self._get_tools(game_state)
        response = self.client.chat.completions.create(
            model=self.model, max_completion_tokens=1024,
            messages=[{"role": "system", "content": system_prompt},
                      {"role": "user", "content": "What do you want to say or do? Call a function."}],
            tools=tools, tool_choice="required",
        )
        action, metadata = self._parse_response(response)
        if action["action"] == "idle":
            if meeting_state.current_round < 2:
                action = {"action": "speak", "params": {"message": "I have nothing conclusive to share."}}
            else:
                action = {"action": "vote", "params": {"target": "skip"}}
        return action, metadata

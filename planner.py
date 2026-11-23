"""A small state-space planner for NPC interactions on the stadium ring.

State: the acting NPC's current zone and whether the requested interaction has
occurred. Move actions require adjacent zones and change the NPC's location;
the interaction action requires reaching the partner's zone. Breadth-first
search returns a shortest action plan.
"""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass
from typing import Dict, Iterable, List, Tuple


@dataclass(frozen=True)
class PlanAction:
    kind: str
    source: str
    destination: str
    label: str = ""

    def describe(self, actor: str, partner: str) -> str:
        if self.kind == "move":
            return f"{actor}: bergerak {self.source} -> {self.destination}"
        return f"{actor}: {self.label} dengan {partner} di {self.destination}"


@dataclass(frozen=True)
class PlanResult:
    actions: Tuple[PlanAction, ...]
    explored_states: int


def plan_interaction(start: str, target: str, graph: Dict[str, Iterable[str]], label: str):
    """Plan moves from start to target, then execute the requested interaction."""
    initial = (start, False)
    frontier = deque([initial])
    previous = {initial: None}
    action_used = {}
    goal = None
    explored = 0

    while frontier:
        state = frontier.popleft()
        zone, completed = state
        explored += 1
        if completed:
            goal = state
            break

        successors = []
        if zone == target:
            successors.append(((zone, True), PlanAction("interact", zone, zone, label)))
        else:
            for neighbor in graph.get(zone, ()):
                successors.append(((neighbor, False), PlanAction("move", zone, neighbor)))

        for next_state, action in successors:
            if next_state in previous:
                continue
            previous[next_state] = state
            action_used[next_state] = action
            frontier.append(next_state)

    if goal is None:
        return PlanResult((), explored)

    actions: List[PlanAction] = []
    cursor = goal
    while previous[cursor] is not None:
        actions.append(action_used[cursor])
        cursor = previous[cursor]
    actions.reverse()
    return PlanResult(tuple(actions), explored)

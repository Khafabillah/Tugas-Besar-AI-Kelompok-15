"""Build current NPC facts, run the stadium KB, and plan inferred interactions."""

from __future__ import annotations

from typing import Dict

import config as cfg
from events import LogicSnapshot
from knowledge_base import RULE_DESCRIPTIONS, STADIUM_RULES
from logic_engine import Atom, forward_chain
from planner import plan_interaction

INTERACTION_LABELS = {
    "ALERT": "peringatan keamanan",
    "ESCORT": "pengawalan",
    "INTERVIEW": "wawancara",
    "SAY_HELLO": "saling menyapa",
    "ASK_DIRECTIONS": "bertanya arah",
}


def _plain(value: str) -> str:
    return value.replace("_", " ")


def _zone_title(zone: str) -> str:
    return cfg.ZONE_LABEL.get(zone, zone)


def _unique_interactions(facts):
    result = []
    seen = set()
    for fact in sorted(facts, key=str):
        if fact.predicate != "Interaction" or len(fact.terms) != 3:
            continue
        left, right, kind = fact.terms
        key = (kind, *sorted((left, right))) if kind == "SAY_HELLO" else (kind, left, right)
        if key in seen:
            continue
        seen.add(key)
        result.append((left, right, kind))
    return result


def evaluate_npc_logic(csp, assignment: Dict[str, str]) -> LogicSnapshot:
    """Evaluate the interaction KB against the assignment currently on screen."""
    initial_facts = []
    npc_locations = {}
    npc_roles = {}
    npc_names = {}

    for zone in csp.variables:
        role = assignment.get(zone)
        if role is None:
            continue
        npc = f"NPC-{cfg.ZONE_NUMBER[zone]:02d}"
        npc_locations[npc] = zone
        npc_roles[npc] = role
        npc_names[npc] = f"{npc} ({_plain(role)} / {_zone_title(zone)})"
        initial_facts.extend((
            Atom("At", (npc, zone)),
            Atom("Role", (npc, role)),
        ))
        if zone != "Transit":
            initial_facts.append(Atom("AwayFromTransit", (npc,)))

    for left, right in csp.edges:
        initial_facts.append(Atom("Adjacent", (left, right)))
        initial_facts.append(Atom("Adjacent", (right, left)))

    all_facts, derivations = forward_chain(initial_facts, STADIUM_RULES)

    facts_text = []
    for npc in sorted(npc_locations):
        zone, role = npc_locations[npc], npc_roles[npc]
        fact_text = f"At({npc}, {zone}) AND Role({npc}, {_plain(role)})"
        if zone != "Transit":
            fact_text += f" AND AwayFromTransit({npc})"
        facts_text.append(fact_text)
    occupied_edges = []
    occupied = set(npc_locations.values())
    for left, right in csp.edges:
        if left in occupied and right in occupied:
            occupied_edges.append(f"Adjacent({left}, {right})")
    facts_text.extend(occupied_edges)
    if not facts_text:
        facts_text.append("Belum ada NPC: jalankan salah satu solver untuk mengisi zona.")

    derivation_text = []
    for proof in derivations:
        premises = " AND ".join(str(atom) for atom in proof.premises)
        derivation_text.append(f"{proof.rule}: {premises} -> {proof.conclusion}")
    if not derivation_text:
        derivation_text.append("Belum ada aturan yang cocok dengan fakta saat ini.")

    interactions = _unique_interactions(all_facts)
    interaction_text = []
    plan_text = []
    physical_graph = {zone: [] for zone in csp.variables}
    for left, right in csp.edges:
        physical_graph[left].append(right)
        physical_graph[right].append(left)

    for left, right, kind in interactions:
        label = INTERACTION_LABELS.get(kind, _plain(kind))
        interaction_text.append(
            f"{npc_names.get(left, left)} -> {npc_names.get(right, right)}: {label}"
        )
        start = npc_locations.get(left)
        target = npc_locations.get(right)
        if start is None or target is None:
            continue
        plan = plan_interaction(start, target, physical_graph, label)
        plan_text.append(f"Tujuan: {label} ({left} ke {right}); ekspansi {plan.explored_states} state")
        if not plan.actions:
            plan_text.append("  Tidak ditemukan rencana pada graf zona.")
        else:
            for index, action in enumerate(plan.actions, 1):
                plan_text.append(f"  {index}. {action.describe(left, right)}")

    if not interaction_text:
        interaction_text.append("Belum ada interaksi yang diturunkan dari fakta saat ini.")
    if not plan_text:
        plan_text.append("Planner menunggu interaksi hasil inferensi.")

    return LogicSnapshot(
        facts=facts_text,
        rules=list(RULE_DESCRIPTIONS),
        derivations=derivation_text,
        interactions=interaction_text,
        plans=plan_text,
    )

"""Small positive-logic inference engine used by the stadium NPC knowledge base.

The engine knows nothing about stadium roles, pygame, or zone layout. It accepts
facts and Horn-style rules and returns the facts derivable by forward chaining.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Iterable, List, Set, Tuple


@dataclass(frozen=True)
class Atom:
    predicate: str
    terms: Tuple[str, ...]

    def __str__(self):
        return f"{self.predicate}({', '.join(self.terms)})"


@dataclass(frozen=True)
class Rule:
    name: str
    premises: Tuple[Atom, ...]
    conclusion: Atom
    description: str


@dataclass(frozen=True)
class Derivation:
    rule: str
    premises: Tuple[Atom, ...]
    conclusion: Atom


Substitution = Dict[str, str]


def _is_variable(term: str) -> bool:
    return term.startswith("?")


def _unify(pattern: Atom, fact: Atom, substitution: Substitution):
    if pattern.predicate != fact.predicate or len(pattern.terms) != len(fact.terms):
        return None
    result = dict(substitution)
    for expected, actual in zip(pattern.terms, fact.terms):
        if _is_variable(expected):
            bound = result.get(expected)
            if bound is not None and bound != actual:
                return None
            result[expected] = actual
        elif expected != actual:
            return None
    return result


def _rule_matches(rule: Rule, facts_by_predicate):
    """Yield substitutions and matched premises for one rule."""
    partial = [({}, ())]
    for premise in rule.premises:
        candidates = facts_by_predicate.get(premise.predicate, ())
        next_partial = []
        for substitution, matched in partial:
            for fact in candidates:
                unified = _unify(premise, fact, substitution)
                if unified is not None:
                    next_partial.append((unified, matched + (fact,)))
        partial = next_partial
        if not partial:
            break
    yield from partial


def forward_chain(initial_facts: Iterable[Atom], rules: Iterable[Rule]):
    """Compute the positive-rule closure and return (facts, proof steps)."""
    facts: Set[Atom] = set(initial_facts)
    ordered_rules = tuple(rules)
    derivations: List[Derivation] = []

    while True:
        facts_by_predicate = {}
        for fact in facts:
            facts_by_predicate.setdefault(fact.predicate, []).append(fact)
        for values in facts_by_predicate.values():
            values.sort(key=str)

        added = False
        for rule in ordered_rules:
            for substitution, premises in _rule_matches(rule, facts_by_predicate):
                conclusion = Atom(
                    rule.conclusion.predicate,
                    tuple(substitution.get(term, term) for term in rule.conclusion.terms),
                )
                if any(_is_variable(term) for term in conclusion.terms):
                    continue
                if conclusion in facts:
                    continue
                facts.add(conclusion)
                derivations.append(Derivation(rule.name, premises, conclusion))
                added = True
        if not added:
            return facts, derivations

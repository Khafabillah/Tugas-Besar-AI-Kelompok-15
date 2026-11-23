"""Declarative stadium NPC knowledge base.

Rules are kept separate from the pygame application and from the inference
engine so game behavior can be edited without changing either component.
Variables use a leading '?' and each rule is a Horn clause.
"""

import config as cfg
from logic_engine import Atom, Rule


def A(predicate, *terms):
    return Atom(predicate, tuple(terms))


STADIUM_RULES = (
    Rule(
        "R1",
        (A("Role", "?home", cfg.TUAN_RUMAH), A("At", "?home", "?home_zone"),
         A("Role", "?away", cfg.TAMU), A("At", "?away", "?away_zone"),
         A("Adjacent", "?home_zone", "?away_zone")),
        A("Interaction", "?home", "?away", "ALERT"),
        "Tuan Rumah dan Tamu bertetangga -> peringatan keamanan.",
    ),
    Rule(
        "R2",
        (A("Role", "?away", cfg.TAMU), A("At", "?away", "?away_zone"),
         A("Role", "?vip", cfg.VIP), A("At", "?vip", "?vip_zone"),
         A("Adjacent", "?away_zone", "?vip_zone")),
        A("Interaction", "?away", "?vip", "ESCORT"),
        "Tamu bertetangga dengan VIP -> petugas memberi pengawalan.",
    ),
    Rule(
        "R3",
        (A("Role", "?away", cfg.TAMU), A("At", "?away", "?away_zone"),
         A("Role", "?media", cfg.MEDIA), A("At", "?media", "?media_zone"),
         A("Adjacent", "?away_zone", "?media_zone")),
        A("Interaction", "?away", "?media", "ESCORT"),
        "Tamu bertetangga dengan Media -> petugas menjaga jalur liputan.",
    ),
    Rule(
        "R4",
        (A("Role", "?media", cfg.MEDIA), A("At", "?media", "?media_zone"),
         A("Role", "?vip", cfg.VIP), A("At", "?vip", "?vip_zone"),
         A("Adjacent", "?media_zone", "?vip_zone")),
        A("Interaction", "?media", "?vip", "INTERVIEW"),
        "Media bertetangga dengan VIP -> dapat melakukan wawancara.",
    ),
    Rule(
        "R5",
        (A("Role", "?left", "?group"), A("At", "?left", "?left_zone"),
         A("Role", "?right", "?group"), A("At", "?right", "?right_zone"),
         A("Adjacent", "?left_zone", "?right_zone")),
        A("Interaction", "?left", "?right", "SAY_HELLO"),
        "Dua penonton dari kelompok yang sama bertetangga -> saling menyapa.",
    ),
    Rule(
        "R6",
        (A("Role", "?visitor", cfg.NETRAL), A("AwayFromTransit", "?visitor"),
         A("At", "?desk", "Transit"), A("Role", "?desk", cfg.NETRAL)),
        A("Interaction", "?visitor", "?desk", "ASK_DIRECTIONS"),
        "Pengunjung Netral di luar Transit -> menuju meja informasi di Transit.",
    ),
)


RULE_DESCRIPTIONS = [f"{rule.name}: {rule.description}" for rule in STADIUM_RULES]

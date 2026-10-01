from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Phenotype:
    name: str
    capabilities: frozenset[str]


PHENOTYPES = {
    "source_investigator": Phenotype("source_investigator", frozenset({"source", "freshness", "independence"})),
    "numerical_verifier": Phenotype("numerical_verifier", frozenset({"numeric", "synthesize"})),
    "counterexample_hunter": Phenotype("counterexample_hunter", frozenset({"counterexample", "source"})),
    "adversarial_critic": Phenotype("adversarial_critic", frozenset({"critic", "entailment"})),
    "synthesizer": Phenotype("synthesizer", frozenset({"synthesize"})),
}

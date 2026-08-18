from __future__ import annotations

from dataclasses import asdict, dataclass, field
from enum import StrEnum
from typing import Any

from mimicus.canonical import sha256_obj


class NodeKind(StrEnum):
    PROFILE = "PROFILE"
    MEMORY_RETRIEVE = "MEMORY_RETRIEVE"
    AUDITION = "AUDITION"
    DECOMPOSE = "DECOMPOSE"
    AGENT_TASK = "AGENT_TASK"
    FALSIFIER = "FALSIFIER"
    CHALLENGE = "CHALLENGE"
    JOIN = "JOIN"
    SYNTHESIS = "SYNTHESIS"
    LEARN = "LEARN"
    GERMINAL = "GERMINAL"


class MorphologyName(StrEnum):
    SOLO = "solo"
    PARALLEL_FANOUT = "parallel_fanout"
    PAIRED_VERIFY = "paired_verify"
    SPARSE_GRAPH = "sparse_graph"
    HIERARCHICAL_FANOUT_FANIN = "hierarchical_fanout_fanin"


@dataclass
class DagNode:
    node_id: str
    kind: NodeKind
    prerequisites: tuple[str, ...] = ()
    identity: str | None = None
    input_hash: str = ""
    budget_usd: float = 0.0
    timeout_s: float = 30.0
    status: str = "PENDING"
    logical_steps: int = 1
    duration_ms: float = 0.0
    output_hash: str = ""
    group: str | None = None

    def semantic_dict(self) -> dict[str, Any]:
        row = asdict(self)
        row.pop("status")
        row.pop("duration_ms")
        row.pop("output_hash")
        return row


@dataclass(frozen=True)
class DagEdge:
    source: str
    target: str
    semantics: str = "dependency"
    group: str | None = None


@dataclass
class MorphologyPlan:
    name: MorphologyName
    nodes: list[DagNode]
    edges: list[DagEdge]
    compiler_rationale: dict[str, Any] = field(default_factory=dict)

    @property
    def plan_hash(self) -> str:
        return sha256_obj({"name": self.name.value, "nodes": [node.semantic_dict() for node in self.nodes], "edges": [asdict(edge) for edge in self.edges], "compiler_rationale": self.compiler_rationale})

    @property
    def structural_signature(self) -> str:
        normalized_nodes = sorted((node.kind.value, node.group or "", len(node.prerequisites)) for node in self.nodes)
        normalized_edges = sorted((next(n.kind.value for n in self.nodes if n.node_id == edge.source), next(n.kind.value for n in self.nodes if n.node_id == edge.target), edge.semantics, edge.group or "") for edge in self.edges)
        return sha256_obj({"nodes": normalized_nodes, "edges": normalized_edges})

    def validate(self) -> None:
        ids = [node.node_id for node in self.nodes]
        if len(ids) != len(set(ids)):
            raise ValueError("duplicate DAG node id")
        id_set = set(ids)
        for node in self.nodes:
            if any(parent not in id_set for parent in node.prerequisites):
                raise ValueError(f"missing prerequisite for {node.node_id}")
            if node.kind in {NodeKind.LEARN, NodeKind.GERMINAL} and not node.prerequisites:
                raise ValueError(f"orphan irreversible node: {node.node_id}")
        incoming = {node_id: 0 for node_id in ids}
        outgoing: dict[str, list[str]] = {node_id: [] for node_id in ids}
        for edge in self.edges:
            if edge.source not in id_set or edge.target not in id_set:
                raise ValueError("DAG edge references missing node")
            incoming[edge.target] += 1
            outgoing[edge.source].append(edge.target)
        ready = sorted(node_id for node_id, degree in incoming.items() if degree == 0)
        seen: list[str] = []
        while ready:
            current = ready.pop(0)
            seen.append(current)
            for child in sorted(outgoing[current]):
                incoming[child] -= 1
                if incoming[child] == 0:
                    ready.append(child)
                    ready.sort()
        if len(seen) != len(ids):
            raise ValueError("morphology DAG contains a cycle")

    def as_dict(self) -> dict[str, Any]:
        return {"name": self.name.value, "plan_hash": self.plan_hash, "structural_signature": self.structural_signature, "nodes": [asdict(node) | {"kind": node.kind.value} for node in self.nodes], "edges": [asdict(edge) for edge in self.edges], "compiler_rationale": self.compiler_rationale}


def _node_id(kind: NodeKind, index: int, identity: str | None = None) -> str:
    return f"{kind.value.lower()}-{index:02d}-{sha256_obj({'kind': kind.value, 'index': index, 'identity': identity})[:10]}"


def compile_morphology(
    *,
    task_hash: str,
    selected_fingerprints: list[str],
    falsifier_hashes: list[str],
    complexity: float,
    required_capabilities: tuple[str, ...],
    max_concurrency: int,
    learn: bool,
    force_sparse: bool = False,
    hierarchical: bool = False,
    morphology_override: MorphologyName | None = None,
) -> MorphologyPlan:
    count = len(selected_fingerprints)
    if morphology_override is not None:
        name = morphology_override
    elif count <= 1:
        name = MorphologyName.SOLO
    elif hierarchical and count >= 3:
        name = MorphologyName.HIERARCHICAL_FANOUT_FANIN
    elif force_sparse or (complexity >= 0.75 and count >= 3):
        name = MorphologyName.SPARSE_GRAPH
    elif count == 2 and len(required_capabilities) <= 1:
        name = MorphologyName.PAIRED_VERIFY
    else:
        name = MorphologyName.PARALLEL_FANOUT

    nodes: list[DagNode] = []
    edges: list[DagEdge] = []
    profile = DagNode(_node_id(NodeKind.PROFILE, 0), NodeKind.PROFILE, input_hash=task_hash)
    memory = DagNode(_node_id(NodeKind.MEMORY_RETRIEVE, 0), NodeKind.MEMORY_RETRIEVE, (profile.node_id,), input_hash=task_hash)
    audition = DagNode(_node_id(NodeKind.AUDITION, 0), NodeKind.AUDITION, (profile.node_id,), input_hash=task_hash)
    nodes.extend([profile, memory, audition])
    edges.extend([DagEdge(profile.node_id, memory.node_id), DagEdge(profile.node_id, audition.node_id)])

    agent_parent_ids = (memory.node_id, audition.node_id)
    if name == MorphologyName.HIERARCHICAL_FANOUT_FANIN:
        decompose = DagNode(_node_id(NodeKind.DECOMPOSE, 0, task_hash), NodeKind.DECOMPOSE, agent_parent_ids, input_hash=task_hash, group="hierarchy-root")
        nodes.append(decompose)
        edges.extend([DagEdge(memory.node_id, decompose.node_id, "decomposition", "hierarchy-root"), DagEdge(audition.node_id, decompose.node_id, "decomposition", "hierarchy-root")])
        agent_parent_ids = (decompose.node_id,)

    agent_nodes: list[DagNode] = []
    for index, fingerprint in enumerate(selected_fingerprints):
        group = "solo" if name == MorphologyName.SOLO else (f"subgroup-{index % 2}" if name == MorphologyName.HIERARCHICAL_FANOUT_FANIN else "fanout")
        node = DagNode(_node_id(NodeKind.AGENT_TASK, index, fingerprint), NodeKind.AGENT_TASK, agent_parent_ids, identity=fingerprint, input_hash=sha256_obj({"task": task_hash, "agent": fingerprint}), group=group)
        agent_nodes.append(node)
        nodes.append(node)
        for parent in node.prerequisites:
            edges.append(DagEdge(parent, node.node_id, "worker_fanout" if name != MorphologyName.SOLO else "dependency", group))

    falsifier_nodes: list[DagNode] = []
    for index, spec_hash in enumerate(falsifier_hashes):
        node = DagNode(_node_id(NodeKind.FALSIFIER, index, spec_hash), NodeKind.FALSIFIER, (memory.node_id,), identity=spec_hash, input_hash=sha256_obj({"task": task_hash, "falsifier": spec_hash}), group="falsifier-fanout")
        falsifier_nodes.append(node)
        nodes.append(node)
        edges.append(DagEdge(memory.node_id, node.node_id, "falsifier_fanout", "falsifier-fanout"))

    if name == MorphologyName.HIERARCHICAL_FANOUT_FANIN:
        subgroup_joins: list[DagNode] = []
        for group_index in (0, 1):
            members = [node for index, node in enumerate(agent_nodes) if index % 2 == group_index]
            if not members:
                continue
            subgroup = DagNode(_node_id(NodeKind.JOIN, group_index + 1, f"subgroup-{group_index}"), NodeKind.JOIN, tuple(node.node_id for node in members), input_hash=task_hash, group=f"subgroup-{group_index}-fanin")
            subgroup_joins.append(subgroup)
            nodes.append(subgroup)
            for member in members:
                edges.append(DagEdge(member.node_id, subgroup.node_id, "nested_fanin", subgroup.group))
        upstream = [node.node_id for node in subgroup_joins] + [node.node_id for node in falsifier_nodes]
    else:
        upstream = [node.node_id for node in agent_nodes + falsifier_nodes] or [audition.node_id]

    if name in {MorphologyName.PAIRED_VERIFY, MorphologyName.SPARSE_GRAPH} and len(agent_nodes) >= 2:
        semantics = "peer_verification" if name == MorphologyName.PAIRED_VERIFY else "sparse_challenge_stage"
        challenge = DagNode(_node_id(NodeKind.CHALLENGE, 0, name.value), NodeKind.CHALLENGE, tuple(agent.node_id for agent in agent_nodes), identity="sparse-policy", input_hash=sha256_obj({"task": task_hash, "morphology": name.value}), group=semantics)
        nodes.append(challenge)
        for parent in challenge.prerequisites:
            edges.append(DagEdge(parent, challenge.node_id, semantics, semantics))
        upstream.append(challenge.node_id)

    join_group = "hierarchy-final-fanin" if name == MorphologyName.HIERARCHICAL_FANOUT_FANIN else ("paired-verified-fanin" if name == MorphologyName.PAIRED_VERIFY else "fanin")
    join = DagNode(_node_id(NodeKind.JOIN, 0, name.value), NodeKind.JOIN, tuple(sorted(set(upstream))), input_hash=task_hash, group=join_group)
    nodes.append(join)
    for parent in join.prerequisites:
        edges.append(DagEdge(parent, join.node_id, "hierarchical_fanin" if name == MorphologyName.HIERARCHICAL_FANOUT_FANIN else "fanin", join_group))
    synthesis = DagNode(_node_id(NodeKind.SYNTHESIS, 0), NodeKind.SYNTHESIS, (join.node_id,), input_hash=task_hash)
    nodes.append(synthesis)
    edges.append(DagEdge(join.node_id, synthesis.node_id))
    if learn:
        learn_node = DagNode(_node_id(NodeKind.LEARN, 0), NodeKind.LEARN, (synthesis.node_id,), input_hash=task_hash)
        germinal = DagNode(_node_id(NodeKind.GERMINAL, 0), NodeKind.GERMINAL, (learn_node.node_id,), input_hash=task_hash)
        nodes.extend([learn_node, germinal])
        edges.extend([DagEdge(synthesis.node_id, learn_node.node_id), DagEdge(learn_node.node_id, germinal.node_id)])

    plan = MorphologyPlan(name=name, nodes=nodes, edges=edges, compiler_rationale={"selected_agents": count, "falsifiers": len(falsifier_hashes), "complexity": complexity, "required_capabilities": list(required_capabilities), "max_concurrency": max_concurrency, "smallest_sufficient": True})
    plan.validate()
    return plan

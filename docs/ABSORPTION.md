# MiMicus-swarm absorption

Source repository: `simondalmasso/MiMicus-swarm`
Source branch: `order-002-mimicus-v01`
Source exact HEAD: `565407eb1296eae617f5b14b512d2e0cf08c6c02`

## Preservation method

The complete source branch was absorbed into this repository with a non-squashed `git subtree add` under:

`archive/MiMicus-swarm-source/`

Because the subtree import is not squashed, the original MiMicus-swarm history is now reachable from the target repository merge history. Deleting the old repository later does not delete this imported history.

The archive is intentionally excluded from the Cloudflare Worker runtime. It remains source-of-truth material for algorithms, evidence, migrations, tests and provenance.

## What is promoted into Mimicus iAffice

The new product keeps these MiMicus principles as architectural contracts:

- one orchestration control plane;
- bounded coalition selection;
- morphologies: solo, paired_verify, parallel_fanout, sparse_graph, hierarchical_fanout_fanin;
- fail-closed verification and claim-bound evidence;
- immutable evidence/provenance;
- governed memory lifecycle;
- no hidden authority expansion;
- explicit external-effect boundaries.

The Cloudflare UI/runtime is a separate edge shell. Python MiMicus remains preserved as the deep research/reference core until individual capabilities are ported or exposed through a deliberate service boundary.

## Deletion checklist for the old repository

Do not delete `MiMicus-swarm` until:
1. this target branch is pushed;
2. the subtree merge commit is visible remotely;
3. `archive/MiMicus-swarm-source/src/mimicus`, tests, docs and evidence are visible;
4. the source SHA above is reachable in target history;
5. a fresh clone of this repository can inspect that subtree.

Only then is deletion of the old repository reversible from this repository alone.

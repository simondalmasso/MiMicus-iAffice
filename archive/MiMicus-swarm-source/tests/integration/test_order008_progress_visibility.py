from mimicus.claims.evidence_bundle import EvidenceInput
from mimicus.orchestration.engine import MiMicusEngine, RunRequest


def test_inspect_state_returns_persisted_progress_in_execution_order(tmp_path) -> None:
    database = f"sqlite:///{tmp_path / 'order008-progress.db'}"
    engine = MiMicusEngine(database)
    run = engine.run(
        RunRequest(
            task="Exercise normal runtime progress persistence.",
            domain="general",
            source_mode="runtime",
            evidence=[
                EvidenceInput(
                    origin="order008://progress-visibility",
                    independence_cluster="order008-progress-visibility",
                    content="runtime progress visibility probe",
                    extracted_facts={"context": "progress-visibility"},
                )
            ],
            max_agents=1,
            learn=False,
        )
    )

    state = engine.repository.inspect_state(run.run_id)
    assert state["progress"]
    assert state["progress"] == run.progress

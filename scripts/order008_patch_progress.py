from pathlib import Path


path = Path("src/mimicus/storage/repository.py")
text = path.read_text(encoding="utf-8")
query_old = """            communications: list[str] = []
            evidence_rows: list[str] = []
            if run_id is not None:
                communication_rows = connection.execute(select(CommunicationRow.payload_json).where(CommunicationRow.run_id == run_id)).scalars().all()
                communications = [str(row) for row in communication_rows if row is not None]
                raw_evidence = connection.execute(select(EvidenceRow.payload_json).where(EvidenceRow.run_id == run_id)).scalars().all()
                evidence_rows = [str(row) for row in raw_evidence if row is not None]
"""
query_new = """            communications: list[str] = []
            evidence_rows: list[str] = []
            progress_rows: list[str] = []
            if run_id is not None:
                communication_rows = connection.execute(select(CommunicationRow.payload_json).where(CommunicationRow.run_id == run_id)).scalars().all()
                communications = [str(row) for row in communication_rows if row is not None]
                raw_evidence = connection.execute(select(EvidenceRow.payload_json).where(EvidenceRow.run_id == run_id)).scalars().all()
                evidence_rows = [str(row) for row in raw_evidence if row is not None]
                raw_progress = (
                    connection.execute(
                        select(ProgressLedgerRow.payload_json)
                        .where(ProgressLedgerRow.run_id == run_id)
                        .order_by(ProgressLedgerRow.step, ProgressLedgerRow.id)
                    )
                    .scalars()
                    .all()
                )
                progress_rows = [str(row) for row in raw_progress if row is not None]
"""
return_old = """            \"communications\": [json.loads(row) for row in communications if row],
            \"evidence\": [json.loads(row) for row in evidence_rows if row],
"""
return_new = """            \"communications\": [json.loads(row) for row in communications if row],
            \"evidence\": [json.loads(row) for row in evidence_rows if row],
            \"progress\": [json.loads(row) for row in progress_rows if row],
"""

already_patched = '"progress": [json.loads(row) for row in progress_rows if row]' in text
if not already_patched:
    if query_old not in text or return_old not in text:
        raise SystemExit("repository.py inspect_state no longer matches expected remote truth")
    text = text.replace(query_old, query_new, 1).replace(return_old, return_new, 1)
    path.write_text(text, encoding="utf-8")

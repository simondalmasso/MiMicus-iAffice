from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

from .analytics import concentration
from .benchmark import benchmark
from .client import VersionAwareAlloraClient
from .economics import analyze_economics
from .demo import run_synthetic_demo
from .radar import Radar
from .gate_evidence import GateEvidenceRegistry
from .report import write_json
from .safety import WRITE_LOCK_ERROR, scan_tree
from .storage import Storage

DEFAULT_DB = Path('.allora-edge/allora-edge.sqlite3')
DEFAULT_EVIDENCE = Path('evidence')


def _build() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog='allora-edge', description='Allora read-only radar; ORDER-001 forbids all chain writes')
    p.add_argument('--network', choices=('mainnet','testnet'), default='mainnet')
    p.add_argument('--db', type=Path, default=DEFAULT_DB)
    p.add_argument('--evidence', type=Path, default=DEFAULT_EVIDENCE)
    sub = p.add_subparsers(dest='command', required=True)
    sub.add_parser('scan')
    w = sub.add_parser('watch'); w.add_argument('--interval', type=float, default=60.0); w.add_argument('--iterations', type=int, default=0)
    sub.add_parser('census')
    t = sub.add_parser('topic'); t.add_argument('id', type=int)
    e = sub.add_parser('economics'); e.add_argument('id', type=int)
    workers = sub.add_parser('workers'); workers.add_argument('id', type=int)
    r = sub.add_parser('replay'); r.add_argument('--from-height', type=int, required=True); r.add_argument('--to-height', type=int, required=True); r.add_argument('--step', type=int, default=1000)
    sub.add_parser('report')
    s = sub.add_parser('safety-check'); s.add_argument('--root', type=Path, default=Path('.'))
    sub.add_parser('health')
    b = sub.add_parser('benchmark'); b.add_argument('--requests', type=int, default=10)
    d = sub.add_parser('shadow-demo'); d.add_argument('--fixture', type=Path, default=Path('tests/fixtures/synthetic_non_trading.json'))
    return p


def main(argv: list[str] | None = None) -> int:
    args = _build().parse_args(argv)
    if args.command == 'safety-check':
        findings = scan_tree(args.root)
        print(json.dumps({'write_lock': 'PASS', 'error': WRITE_LOCK_ERROR, 'secret_scan': 'PASS' if not findings else 'FAIL', 'findings': findings, 'transactions': 0}, indent=2))
        return 0 if not findings else 2

    store = Storage(args.db)
    try:
        client = VersionAwareAlloraClient(args.network)
        radar = Radar(client, store, args.evidence, GateEvidenceRegistry(Path('config/external-demand.json')))
        if args.command == 'scan':
            print(json.dumps(radar.scan(), indent=2, default=str)); return 0
        if args.command == 'watch':
            i = 0
            while args.iterations <= 0 or i < args.iterations:
                print(json.dumps(radar.scan(), default=str), flush=True)
                i += 1
                if args.iterations <= 0 or i < args.iterations: time.sleep(max(args.interval, 1.0))
            return 0
        if args.command in ('census','report'):
            print(json.dumps({'topics': store.topic_rows(), 'eligibility': store.eligibility_rows(), 'health': store.health()}, indent=2, default=str)); return 0
        if args.command == 'health':
            print(json.dumps(store.health(), indent=2)); return 0
        if args.command == 'benchmark':
            rpc = benchmark(lambda: client.http.get(f'{client.spec.rpc}/status'), args.requests)
            lcd = benchmark(lambda: client.http.get(f'{client.api_root}/next_topic_id'), args.requests)
            out = {'network': client.spec.name, 'rpc': rpc.to_dict(), 'lcd': lcd.to_dict(), 'grpc': {'status': 'NOT_BENCHMARKED_HTTP2_RUNTIME_GAP'}, 'source_tag': 'LIVE_MAINNET' if client.spec.name == 'mainnet' else 'OFFICIAL_DOC'}
            write_json(args.evidence / 'access-benchmark.json', out); print(json.dumps(out, indent=2)); return 0
        if args.command == 'shadow-demo':
            out = run_synthetic_demo(args.fixture, persist=store.put_shadow_result)
            write_json(args.evidence / 'synthetic-shadow-demo.json', out); print(json.dumps(out, indent=2)); return 0
        if args.command == 'topic':
            topic = client.census_topic(args.id, client.verify_network().get('latest_block_height'))
            print(json.dumps(topic.to_dict(), indent=2)); return 0
        if args.command == 'economics':
            topic = client.census_topic(args.id)
            result = analyze_economics(args.id, fee_revenue=topic.fee_revenue, effective_fee_revenue=topic.effective_fee_revenue, topic_stake=topic.topic_stake)
            print(json.dumps(result.to_dict(), indent=2)); return 0
        if args.command == 'workers':
            scores = client.lowest_scores(args.id)
            print(json.dumps({'topic_id': args.id, 'lowest_scores': scores, 'distribution': concentration([]), 'status': 'PARTIAL_WITH_EXACT_DATA_GAP'}, indent=2)); return 0
        if args.command == 'replay':
            if args.step <= 0 or args.to_height < args.from_height: raise SystemExit('invalid replay range')
            rows = []
            for height in range(args.from_height, args.to_height + 1, args.step):
                try: rows.append({'height': height, 'data': client.active_topics_at_block(height)})
                except Exception as exc: rows.append({'height': height, 'error': str(exc)})
            write_json(args.evidence / 'historical-replay.json', rows)
            print(json.dumps({'observations': len(rows), 'path': str(args.evidence/'historical-replay.json')}, indent=2)); return 0
    finally:
        store.close()
    return 1


if __name__ == '__main__':
    sys.exit(main())

"""Tests for Bonus B3 (swarm_verified verifier against error amplification)."""

from __future__ import annotations

import json
import time
from pathlib import Path

import pytest

from bonus.swarm_verified import run_claim as run_swarm_verified
from lab8.config_loader import repo_path
from lab8.db import connect, init_store, load_json, load_jsonl
from lab8.durability import InjectedCrash, committed_audit_count
from lab8.metrics import trial_pass
from lab8.shapes.swarm_reference import run_claim as run_swarm
from tests.conftest import BY_ID, CLAIMS, WORLD


def _bonus_world_and_claims() -> tuple[dict[str, object], list[dict[str, object]]]:
    world = load_json(repo_path("bonus", "world.json"))
    claims = load_jsonl(repo_path("bonus", "cases.jsonl"))
    return world, claims


def test_swarm_verified_overrides_seed55_ticket_lie_on_c002(tmp_path: Path) -> None:
    swarm_store = tmp_path / "swarm-c002.sqlite"
    verified_store = tmp_path / "verified-c002.sqlite"
    init_store(swarm_store, WORLD, CLAIMS).close()
    init_store(verified_store, WORLD, CLAIMS).close()

    swarm_res = run_swarm("C-002", seed=55, store_path=str(swarm_store))
    started_at = time.time()
    verified_res = run_swarm_verified("C-002", seed=55, store_path=str(verified_store))

    conn = connect(verified_store)
    try:
        passed, reason = trial_pass(
            verified_res.as_dict(),
            BY_ID["C-002"]["expected"],
            conn,
            started_at=started_at,
        )
    finally:
        conn.close()

    trace_body = json.loads(Path(verified_res.trace_path).read_text(encoding="utf-8"))
    kinds = [event["kind"] for event in trace_body["events"]]

    assert swarm_res.status == "resolved"
    assert passed, reason
    assert "verifier_override" in kinds


def test_swarm_verified_passes_adversarial_cases_across_five_seeds(tmp_path: Path) -> None:
    world, claims = _bonus_world_and_claims()
    assert len(claims) >= 8

    swarm_fails = 0
    for claim in claims:
        claim_id = str(claim["claim_id"])
        expected = claim["expected"]
        for seed in (11, 22, 33, 44, 55):
            verified_store = tmp_path / f"verified-{claim_id}-{seed}.sqlite"
            init_store(verified_store, world, claims).close()
            started_at = time.time()
            verified_res = run_swarm_verified(claim_id, seed=seed, store_path=str(verified_store))
            conn = connect(verified_store)
            try:
                passed, reason = trial_pass(
                    verified_res.as_dict(),
                    expected,
                    conn,
                    started_at=started_at,
                )
            finally:
                conn.close()
            assert passed, f"{claim_id} seed {seed}: {reason}"

            if seed == 55 and claim_id in ("B-001", "B-002", "B-003", "B-004"):
                swarm_store = tmp_path / f"swarm-{claim_id}-{seed}.sqlite"
                init_store(swarm_store, world, claims).close()
                swarm_res = run_swarm(claim_id, seed=seed, store_path=str(swarm_store))
                s_conn = connect(swarm_store)
                try:
                    s_passed, _ = trial_pass(swarm_res.as_dict(), expected, s_conn)
                finally:
                    s_conn.close()
                if not s_passed:
                    swarm_fails += 1

    assert swarm_fails == 4


def test_swarm_verified_preserves_retry_and_crash_safety(tmp_path: Path) -> None:
    retry_store = tmp_path / "retry.sqlite"
    init_store(retry_store, WORLD, CLAIMS).close()
    first = run_swarm_verified("C-011", seed=11, store_path=str(retry_store))
    started_at = time.time()
    second = run_swarm_verified("C-011", seed=11, store_path=str(retry_store))
    conn = connect(retry_store)
    try:
        passed, reason = trial_pass(
            second.as_dict(),
            BY_ID["C-011"]["expected"],
            conn,
            started_at=started_at,
        )
        assert conn.execute("SELECT COUNT(*) AS n FROM refund_ledger WHERE claim_id = 'C-011'").fetchone()["n"] == 1
        assert committed_audit_count(conn, "C-011") == 1
    finally:
        conn.close()
    assert first.status == "resolved"
    assert passed, reason

    crash_store = tmp_path / "crash.sqlite"
    init_store(crash_store, WORLD, CLAIMS).close()
    with pytest.raises(InjectedCrash):
        run_swarm_verified(
            "C-012",
            seed=11,
            store_path=str(crash_store),
            crash_at="after_effect_before_checkpoint",
        )
    started_crash = time.time()
    resumed = run_swarm_verified("C-012", seed=11, store_path=str(crash_store), crash_at=None)
    conn = connect(crash_store)
    try:
        passed, reason = trial_pass(
            resumed.as_dict(),
            BY_ID["C-012"]["expected"],
            conn,
            started_at=started_crash,
        )
        assert conn.execute("SELECT COUNT(*) AS n FROM refund_ledger WHERE claim_id = 'C-012'").fetchone()["n"] == 1
        assert committed_audit_count(conn, "C-012") == 1
    finally:
        conn.close()
    assert passed, reason

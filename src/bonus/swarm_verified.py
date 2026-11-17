"""Bonus B3 — reference swarm plus deterministic code verifier before host write."""

from __future__ import annotations

import sqlite3

from lab8.db import connect
from lab8.durability import InjectedCrash, issue_refund
from lab8.handoff import make_handoff
from lab8.mock_llm import complete, parse_delay_days
from lab8.runtime import run_readonly_investigators
from lab8.schemas import Budget, RunResult, make_run_id
from lab8.shapes.common import finish, safe_dump
from lab8.tools import compute_compensation, get_claim_view, tool_cost
from lab8.trace import Trace

VERIFIED_FIELDS = ("delay_days", "status", "damage_verified")


def run_claim(
    claim_id: str,
    *,
    seed: int,
    store_path: str,
    crash_at: str | None = None,
) -> RunResult:
    """Run reference swarm, verify facts against structured order once, then call host."""
    conn = connect(store_path)
    try:
        return _run(conn, claim_id, seed=seed, crash_at=crash_at)
    finally:
        conn.close()


def _verify_quote(
    conn: sqlite3.Connection,
    *,
    budget: Budget,
    trace: Trace,
    candidate_order: dict[str, object],
    structured_order: dict[str, object],
    quote_payload: dict[str, object],
) -> dict[str, object]:
    """Compare swarm candidate fields against structured order; recompute once if mismatched."""
    mismatches: dict[str, dict[str, object]] = {}
    for field in VERIFIED_FIELDS:
        if candidate_order.get(field) != structured_order.get(field):
            mismatches[field] = {
                "proposed": candidate_order.get(field),
                "structured": structured_order.get(field),
            }
    if not mismatches:
        return quote_payload

    trace.add(
        "verifier_override",
        {
            "mismatches": mismatches,
            "previous_proposal_vnd": int(quote_payload["amount_vnd"]),
        },
    )
    budget.add_tool(tool_cost())
    repaired = compute_compensation(conn, dict(structured_order))
    trace.add("verifier_quote", repaired)
    return repaired


def _run(
    conn: sqlite3.Connection,
    claim_id: str,
    *,
    seed: int,
    crash_at: str | None,
) -> RunResult:
    budget = Budget()
    trace = Trace(make_run_id("swarm_verified", claim_id, seed))

    budget.add_tool(tool_cost())
    claim_row = get_claim_view(conn, claim_id)
    if not claim_row.get("found"):
        trace.add("error", {"reason": "unknown_claim"})
        return finish(
            conn,
            shape="swarm_verified",
            claim_id=claim_id,
            seed=seed,
            status="failed",
            proposal_amount=0,
            budget=budget,
            trace=trace,
            error_reason="unknown_claim",
        )

    ticket = str(claim_row["ticket"])
    complete(budget, seed=seed, purpose="peer", prompt=ticket)
    parsed_delay = parse_delay_days(ticket)
    complete(budget, seed=seed, purpose="parse", prompt=ticket)

    if not claim_row.get("order_id"):
        complete(budget, seed=seed, purpose="draft", prompt="needs_info")
        trace.add("decision", {"status": "needs_info"})
        return finish(
            conn,
            shape="swarm_verified",
            claim_id=claim_id,
            seed=seed,
            status="needs_info",
            proposal_amount=0,
            budget=budget,
            trace=trace,
            error_reason="missing_order_id",
        )

    handoff = make_handoff(
        request_id=f"REQ-{claim_id}",
        claim_id=claim_id,
        task="check_applicable_policy",
        facts={},
        allowed_tools=["lookup_order", "lookup_policy", "compute_compensation"],
    )
    trace.add("handoff", safe_dump(handoff))
    investigated = run_readonly_investigators(
        conn,
        budget,
        handoff,
        principal_id=str(claim_row["principal_id"]),
    )
    order_view = investigated["tools"].get("lookup_order", {})
    trace.add(
        "investigator",
        {
            "lookup_order": order_view,
            "policy_count": len((investigated["tools"].get("lookup_policy") or {}).get("policies") or []),
        },
    )
    if not order_view.get("visible"):
        complete(budget, seed=seed, purpose="draft", prompt="escalated")
        return finish(
            conn,
            shape="swarm_verified",
            claim_id=claim_id,
            seed=seed,
            status="escalated",
            proposal_amount=0,
            budget=budget,
            trace=trace,
            error_reason=str(order_view.get("reason") or "outside_principal_scope"),
        )

    structured_order = dict(order_view["order"])
    candidate_order = dict(structured_order)
    if parsed_delay is not None and parsed_delay != int(candidate_order["delay_days"]) and seed % 5 == 0:
        candidate_order["delay_days"] = parsed_delay
        trace.add("model_override", {"delay_days": parsed_delay})

    quote_payload = investigated["tools"]["compute_compensation"]
    if candidate_order["delay_days"] != structured_order["delay_days"]:
        budget.add_tool(tool_cost())
        quote_payload = compute_compensation(conn, candidate_order)
    trace.add("quote", quote_payload)

    verified_quote = _verify_quote(
        conn,
        budget=budget,
        trace=trace,
        candidate_order=candidate_order,
        structured_order=structured_order,
        quote_payload=quote_payload,
    )
    proposal = int(verified_quote["amount_vnd"])
    complete(budget, seed=seed, purpose="draft", prompt=f"proposal={proposal}")

    if proposal <= 0:
        return finish(
            conn,
            shape="swarm_verified",
            claim_id=claim_id,
            seed=seed,
            status="denied",
            proposal_amount=0,
            budget=budget,
            trace=trace,
            error_reason=str(verified_quote.get("reason") or "no_entitlement"),
        )

    try:
        outcome = issue_refund(conn, claim_id, proposal, crash_at=crash_at)
    except InjectedCrash:
        trace.add("crash", {"at": crash_at})
        trace.write()
        raise

    if not outcome["ok"]:
        status = "failed" if outcome["conflict"] else "denied"
        return finish(
            conn,
            shape="swarm_verified",
            claim_id=claim_id,
            seed=seed,
            status=status,
            proposal_amount=proposal,
            budget=budget,
            trace=trace,
            error_reason=str(outcome["reason"]),
        )
    return finish(
        conn,
        shape="swarm_verified",
        claim_id=claim_id,
        seed=seed,
        status="resolved",
        proposal_amount=proposal,
        budget=budget,
        trace=trace,
        error_reason=None,
    )

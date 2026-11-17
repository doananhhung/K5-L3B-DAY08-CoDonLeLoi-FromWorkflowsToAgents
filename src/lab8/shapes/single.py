"""Shape B — one ReAct agent. Student work.

Use `lab8.runtime.run_react` with max_steps=8. `decide` may pick a read tool.
It must not call `issue_refund`. After the loop, the host validates the quote
and is the only writer.

A decide() that trusts ticket text over the order row will fail hidden claims
where the customer overstates the delay or cites a superseded clause.

Per-order cap: an order may already have been refunded by an earlier claim.
The read tool `lookup_refund_history` shows how much. The host still enforces
the cap, so pass the full quote to `durability.issue_refund`, not a net amount.

Caps: stop at 8 steps. Count model calls in the Budget so cost stays comparable.

Trace contract v1 (docs/contracts.md): return a trace_path to a JSON file written in this run,
{"run_id": <same run_id>, "events": [...]}, on every return path including early
ones. `lab8.trace.Trace` does this; your own tracer is fine if it matches.
"""

from __future__ import annotations

import sqlite3

from lab8.db import connect
from lab8.durability import InjectedCrash, issue_refund
from lab8.mock_llm import complete
from lab8.runtime import run_react
from lab8.schemas import Budget, RunResult, make_run_id
from lab8.shapes.common import finish
from lab8.trace import Trace


def run_claim(
    claim_id: str,
    *,
    seed: int,
    store_path: str,
    crash_at: str | None = None,
) -> RunResult:
    """Execute the single ReAct agent shape (max 8 read-only steps, host-only write)."""
    conn = connect(store_path)
    try:
        return _run(conn, claim_id, seed=seed, crash_at=crash_at)
    finally:
        conn.close()


def _run(
    conn: sqlite3.Connection,
    claim_id: str,
    *,
    seed: int,
    crash_at: str | None,
) -> RunResult:
    budget = Budget()
    trace = Trace(make_run_id("single", claim_id, seed))
    collected: dict[str, dict[str, object]] = {}

    def decide(obs: dict[str, object]) -> dict[str, object]:
        last_tool = obs.get("last_tool")
        last_result = obs.get("last_result")

        if last_tool is None:
            complete(budget, seed=seed, purpose="react_step_1", prompt=f"claim={claim_id}")
            trace.add("react_step", {"step": 1, "action": "get_claim_view"})
            return {"tool": "get_claim_view", "args": {"claim_id": claim_id}}

        if not isinstance(last_result, dict):
            return {"final": {"status": "failed", "proposal_amount": 0, "error_reason": "invalid_tool_result"}}

        if last_tool == "get_claim_view":
            collected["claim"] = last_result
            trace.add(
                "claim",
                {
                    "claim_id": claim_id,
                    "found": bool(last_result.get("found")),
                    "order_id": last_result.get("order_id"),
                },
            )
            complete(budget, seed=seed, purpose="react_step_2", prompt=f"found={bool(last_result.get('found'))}")
            if not last_result.get("found"):
                return {"final": {"status": "failed", "proposal_amount": 0, "error_reason": "unknown_claim"}}
            order_id = last_result.get("order_id")
            if not order_id:
                complete(budget, seed=seed, purpose="draft", prompt="needs_info")
                return {"final": {"status": "needs_info", "proposal_amount": 0, "error_reason": "missing_order_id"}}
            trace.add("react_step", {"step": 2, "action": "lookup_order"})
            return {
                "tool": "lookup_order",
                "args": {"order_id": order_id, "principal_id": last_result["principal_id"]},
            }

        if last_tool == "lookup_order":
            collected["order_view"] = last_result
            trace.add("lookup_order", last_result)
            visible = bool(last_result.get("visible"))
            complete(budget, seed=seed, purpose="react_step_3", prompt=f"visible={visible}")
            if not visible:
                reason = str(last_result.get("reason") or "outside_principal_scope")
                complete(budget, seed=seed, purpose="draft", prompt="escalated")
                return {"final": {"status": "escalated", "proposal_amount": 0, "error_reason": reason}}
            claim_view = collected["claim"]
            trace.add("react_step", {"step": 3, "action": "lookup_refund_history"})
            return {
                "tool": "lookup_refund_history",
                "args": {"order_id": claim_view["order_id"], "principal_id": claim_view["principal_id"]},
            }

        if last_tool == "lookup_refund_history":
            collected["refund_history"] = last_result
            trace.add("lookup_refund_history", last_result)
            order_obj = collected["order_view"].get("order")
            if not isinstance(order_obj, dict):
                return {"final": {"status": "failed", "proposal_amount": 0, "error_reason": "missing_order_payload"}}
            complete(
                budget,
                seed=seed,
                purpose="react_step_4",
                prompt=f"refunded={last_result.get('refunded_vnd')}",
            )
            trace.add("react_step", {"step": 4, "action": "compute_compensation"})
            return {"tool": "compute_compensation", "args": {"order": dict(order_obj)}}

        if last_tool == "compute_compensation":
            proposal = int(last_result["amount_vnd"])
            trace.add("quote", last_result)
            complete(budget, seed=seed, purpose="draft", prompt=f"proposal={proposal}")
            if proposal <= 0:
                reason = str(last_result.get("reason") or "no_entitlement")
                return {"final": {"status": "denied", "proposal_amount": 0, "error_reason": reason}}
            return {"final": {"status": "ready_to_refund", "proposal_amount": proposal, "error_reason": None}}

        return {"final": {"status": "failed", "proposal_amount": 0, "error_reason": "unexpected_tool"}}

    react_outcome = run_react(
        conn,
        budget,
        observation={"claim": {"claim_id": claim_id}},
        decide=decide,
        max_steps=8,
        worker=True,
    )
    if react_outcome["stopped"] != "final":
        trace.add("decision", {"status": "failed", "reason": "step_cap"})
        return finish(
            conn,
            shape="single",
            claim_id=claim_id,
            seed=seed,
            status="failed",
            proposal_amount=0,
            budget=budget,
            trace=trace,
            error_reason="step_cap",
        )

    final = react_outcome["final"]
    final_status = str(final["status"])
    if final_status != "ready_to_refund":
        error_reason = final.get("error_reason")
        trace.add("decision", {"status": final_status, "reason": error_reason})
        return finish(
            conn,
            shape="single",
            claim_id=claim_id,
            seed=seed,
            status=final_status,
            proposal_amount=0,
            budget=budget,
            trace=trace,
            error_reason=str(error_reason) if error_reason is not None else None,
        )

    proposal = int(final["proposal_amount"])
    try:
        outcome = issue_refund(conn, claim_id, proposal, crash_at=crash_at)
    except InjectedCrash:
        trace.add("crash", {"at": crash_at})
        trace.write()
        raise

    if not outcome["ok"]:
        status = "failed" if outcome["conflict"] else "denied"
        reason = str(outcome["reason"])
        trace.add("host_refund", {"ok": False, "conflict": bool(outcome["conflict"]), "reason": reason})
        return finish(
            conn,
            shape="single",
            claim_id=claim_id,
            seed=seed,
            status=status,
            proposal_amount=proposal,
            budget=budget,
            trace=trace,
            error_reason=reason,
        )

    trace.add("host_refund", {"ok": True, "reason": outcome["reason"]})
    return finish(
        conn,
        shape="single",
        claim_id=claim_id,
        seed=seed,
        status="resolved",
        proposal_amount=proposal,
        budget=budget,
        trace=trace,
        error_reason=None,
    )

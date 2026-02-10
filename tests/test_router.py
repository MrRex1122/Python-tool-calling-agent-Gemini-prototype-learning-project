"""Router parsing tests.

These tests do not require external API calls.
"""

from agents.router import parse_router_response


def test_parse_router_json_direct() -> None:
    decision = parse_router_response('{"route": "direct", "reason": "simple"}')
    assert decision is not None
    assert decision.route == "direct"
    assert "simple" in decision.reason


def test_parse_router_json_plan_alias() -> None:
    decision = parse_router_response('{"route": "multi", "reason": "tools"}')
    assert decision is not None
    assert decision.route == "plan"


def test_parse_router_fallback_keyword() -> None:
    decision = parse_router_response("I think this needs a plan with tools.")
    assert decision is not None
    assert decision.route == "plan"


def test_parse_router_failure_returns_none() -> None:
    decision = parse_router_response("no keywords here")
    assert decision is None

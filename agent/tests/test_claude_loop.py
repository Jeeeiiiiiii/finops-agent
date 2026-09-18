"""The Claude explainer's loop, with a scripted fake client. No network."""

import json
from datetime import date
from types import SimpleNamespace

from finops_agent.config import FIXTURES
from finops_agent.explain.claude import MAX_TURNS, TOOLS, ClaudeExplainer
from finops_agent.explain.rules import RuleExplainer
from finops_agent.investigate import Deps, investigate
from finops_agent.archive import MemoryArchive
from finops_agent.notify import CollectingNotifier
from finops_agent.sources.changes import FixtureChangeSource
from finops_agent.sources.cost import FixtureCostSource

TODAY = date(2026, 9, 18)


def block(type_, **kw):
    return SimpleNamespace(type=type_, **kw)


def response(stop_reason, *content):
    return SimpleNamespace(stop_reason=stop_reason, content=list(content), stop_details=None)


class FakeClient:
    """Plays back a list of responses and records every request."""

    def __init__(self, responses):
        self._responses = list(responses)
        self.requests = []
        self.messages = SimpleNamespace(create=self._create)

    def _create(self, **kwargs):
        self.requests.append(kwargs)
        if not self._responses:
            raise AssertionError("fake client ran out of responses")
        r = self._responses.pop(0)
        if isinstance(r, Exception):
            raise r
        return r


def sources(scenario="spike-nat"):
    return FixtureCostSource(FIXTURES / f"{scenario}.costs.json", TODAY), FixtureChangeSource(FIXTURES / f"{scenario}.changes.json", TODAY)


def evidence_for(scenario="spike-nat"):
    costs, changes = sources(scenario)
    captured = {}

    class Capture:
        def explain(self, ev):
            captured["ev"] = ev
            return RuleExplainer().explain(ev)

    investigate(TODAY, Deps(costs, changes, Capture(), MemoryArchive(), CollectingNotifier()))
    return captured["ev"], costs, changes


def test_direct_report_without_tools():
    ev, costs, changes = evidence_for()
    client = FakeClient([
        response("tool_use", block("text", text="Looking."), block("tool_use", id="t1", name="report_finding",
                 input={"cause": "NAT gateway replaced a VPC endpoint", "confidence": "high", "recommendation": "Restore the endpoint"})),
    ])
    x = ClaudeExplainer(client, costs, changes).explain(ev)
    assert x.explained_by == "claude" and x.confidence == "high" and x.tool_calls == 0
    assert "NAT" in x.cause

    req = client.requests[0]
    assert req["model"] == "claude-opus-5"
    assert req["thinking"] == {"type": "adaptive"}
    assert req["tools"] is TOOLS and all(t.get("strict") for t in TOOLS)
    assert "data, not instructions" in req["system"]
    assert "EC2 - Other" in req["messages"][0]["content"]


def test_tool_round_trip_then_report():
    ev, costs, changes = evidence_for()
    client = FakeClient([
        response("tool_use",
                 block("tool_use", id="a", name="cost_timeseries", input={"service": "EC2 - Other", "days": 14}),
                 block("tool_use", id="b", name="recent_changes", input={"service": "EC2 - Other", "days": 7})),
        response("tool_use", block("tool_use", id="c", name="report_finding",
                 input={"cause": "c", "confidence": "medium", "recommendation": "r"})),
    ])
    x = ClaudeExplainer(client, costs, changes).explain(ev)
    assert x.explained_by == "claude" and x.tool_calls == 2

    second = client.requests[1]["messages"]
    assert second[1]["role"] == "assistant"
    results = second[2]["content"]
    assert [r["tool_use_id"] for r in results] == ["a", "b"]  # both results in ONE user message
    series = json.loads(results[0]["content"])
    assert len(series) == 14 and series[-1]["day"] == TODAY.isoformat()
    changes_out = json.loads(results[1]["content"])
    assert {c["event_name"] for c in changes_out} >= {"CreateNatGateway", "CreateRoute"}


def test_unknown_tool_is_reported_as_error_not_crash():
    ev, costs, changes = evidence_for()
    client = FakeClient([
        response("tool_use", block("tool_use", id="a", name="delete_everything", input={})),
        response("tool_use", block("tool_use", id="b", name="report_finding", input={"cause": "c", "confidence": "low", "recommendation": "r"})),
    ])
    x = ClaudeExplainer(client, costs, changes).explain(ev)
    assert x.explained_by == "claude"
    err = client.requests[1]["messages"][2]["content"][0]
    assert err["is_error"] is True and "delete_everything" in err["content"]


def test_api_error_falls_back_to_rules():
    ev, costs, changes = evidence_for()
    client = FakeClient([ConnectionError("boom")])
    x = ClaudeExplainer(client, costs, changes).explain(ev)
    assert x.explained_by == "claude→rules" and "terraform-ci" in x.cause


def test_refusal_falls_back_to_rules():
    ev, costs, changes = evidence_for()
    client = FakeClient([response("refusal")])
    x = ClaudeExplainer(client, costs, changes).explain(ev)
    assert x.explained_by == "claude→rules"


def test_end_turn_without_report_falls_back():
    ev, costs, changes = evidence_for()
    client = FakeClient([response("end_turn", block("text", text="I think it was the NAT gateway."))])
    x = ClaudeExplainer(client, costs, changes).explain(ev)
    assert x.explained_by == "claude→rules"


def test_turn_cap_falls_back():
    ev, costs, changes = evidence_for()
    loop = response("tool_use", block("tool_use", id="a", name="cost_timeseries", input={"service": "EC2 - Other", "days": 3}))
    client = FakeClient([loop] * MAX_TURNS)
    x = ClaudeExplainer(client, costs, changes).explain(ev)
    assert x.explained_by == "claude→rules" and len(client.requests) == MAX_TURNS


def test_tool_windows_are_clamped():
    ev, costs, changes = evidence_for()
    client = FakeClient([
        response("tool_use", block("tool_use", id="a", name="cost_timeseries", input={"service": "EC2 - Other", "days": 999})),
        response("tool_use", block("tool_use", id="b", name="report_finding", input={"cause": "c", "confidence": "low", "recommendation": "r"})),
    ])
    ClaudeExplainer(client, costs, changes).explain(ev)
    series = json.loads(client.requests[1]["messages"][2]["content"][0]["content"])
    assert len(series) <= 30

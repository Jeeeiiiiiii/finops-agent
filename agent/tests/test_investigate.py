"""The deep module through its one interface, with fakes at every seam."""

from datetime import date, timedelta
from pathlib import Path

from finops_agent.archive import MemoryArchive
from finops_agent.config import FIXTURES
from finops_agent.explain import RuleExplainer
from finops_agent.investigate import Deps, digest, investigate
from finops_agent.models import Anomaly, Evidence, Explanation
from finops_agent.notify import CollectingNotifier
from finops_agent.sources.changes import FixtureChangeSource
from finops_agent.sources.cost import FixtureCostSource

TODAY = date(2026, 9, 18)


def deps_for(scenario: str, **overrides) -> tuple[Deps, CollectingNotifier, MemoryArchive]:
    notifier = CollectingNotifier()
    archive = MemoryArchive()
    costs = FixtureCostSource(FIXTURES / f"{scenario}.costs.json", TODAY)
    changes_path = FIXTURES / f"{scenario}.changes.json"
    d = Deps(
        costs=costs,
        changes=FixtureChangeSource(changes_path if changes_path.exists() else None, TODAY),
        explainer=overrides.pop("explainer", RuleExplainer()),
        archive=archive,
        notifier=notifier,
        **overrides,
    )
    return d, notifier, archive


def test_quiet_week_sends_nothing_and_archives_nothing():
    d, notifier, archive = deps_for("quiet")
    report = investigate(TODAY, d)
    assert report.findings == [] and report.notified is False
    assert notifier.sent == [] and archive.items == {}
    assert report.services_seen == 7 and report.account_total_usd > 0


def test_nat_spike_is_found_explained_archived_and_sent():
    d, notifier, archive = deps_for("spike-nat")
    report = investigate(TODAY, d)
    [f] = report.findings
    assert f.service == "EC2 - Other" and f.evidence.anomaly.kind == "spike"
    # Only ec2 write events in the window; the S3 PutObject and the DescribeInstances are filtered out.
    assert {c.event_name for c in f.evidence.changes} == {"CreateNatGateway", "CreateRoute", "DeleteVpcEndpoints"}
    assert f.explanation.explained_by == "rules" and "terraform-ci" in f.explanation.cause
    assert (TODAY, "ec2-other") in archive.items
    assert len(notifier.sent) == 1 and "EC2 - Other" in notifier.sent[0] and "CreateRoute" in notifier.sent[0]
    assert report.notified


def test_repeat_spike_is_archived_but_suppressed():
    d, notifier, archive = deps_for("spike-nat")
    investigate(TODAY - timedelta(days=1), d)  # yesterday's run (fixture offsets shift with the day)
    assert len(notifier.sent) == 1
    report = investigate(TODAY, d)
    [f] = report.findings
    assert f.suppressed and "alerted on" in f.suppressed_reason
    assert (TODAY, "ec2-other") in archive.items  # still archived
    assert len(notifier.sent) == 1 and report.notified is False
    assert any("suppressed" in n for n in report.notes)


def test_dedupe_window_expires():
    # An alert two days ago: suppresses today with a 3-day window, not with a 1-day one.
    d3, _, archive3 = deps_for("spike-nat", dedupe_days=3)
    old = investigate(TODAY, d3).findings[0]
    old.evidence = Evidence(
        Anomaly(old.service, TODAY - timedelta(days=2), 1, 1, 1, 1, "spike"), (), (), 1
    )
    archive3.items.clear()
    archive3.put(old)
    assert investigate(TODAY, d3).findings[0].suppressed

    d1, notifier1, archive1 = deps_for("spike-nat", dedupe_days=1)
    archive1.put(old)
    report = investigate(TODAY, d1)
    assert not report.findings[0].suppressed and len(notifier1.sent) == 1


def test_usage_spike_has_no_changes_and_says_so():
    d, notifier, _ = deps_for("usage-spike")
    [f] = investigate(TODAY, d).findings
    assert f.evidence.changes == () and f.explanation.confidence == "low"
    assert "none found" in notifier.sent[0]


def test_multi_is_ordered_by_impact_and_capped():
    d, _, _ = deps_for("multi")
    report = investigate(TODAY, d)
    assert [f.service for f in report.findings] == ["EC2 - Other", "Amazon Relational Database Service"]
    d2, _, _ = deps_for("multi", max_findings=1)
    report2 = investigate(TODAY, d2)
    assert [f.service for f in report2.findings] == ["EC2 - Other"]
    assert any("Amazon Relational Database Service" in n for n in report2.notes)


def test_explainer_failure_does_not_lose_the_alert():
    class Broken:
        def explain(self, evidence):
            raise RuntimeError("model down")

    class Wrapped:
        """What ClaudeExplainer does: try, then fall to rules."""

        def explain(self, evidence):
            try:
                return Broken().explain(evidence)
            except RuntimeError:
                r = RuleExplainer().explain(evidence)
                return Explanation(r.cause, r.confidence, r.recommendation, "claude→rules")

    d, notifier, _ = deps_for("spike-nat", explainer=Wrapped())
    [f] = investigate(TODAY, d).findings
    assert f.explanation.explained_by == "claude→rules" and len(notifier.sent) == 1


def test_digest_summarises_the_window():
    d, notifier, _ = deps_for("multi")
    investigate(TODAY, d)
    text = digest(TODAY, d, days=7)
    assert "FinOps weekly" in text and "EC2 - Other" in text and "Relational" in text
    assert notifier.sent[-1] == text


def test_fixture_files_exist_for_every_scenario():
    for name in ["quiet", "spike-nat", "new-service", "usage-spike", "multi"]:
        assert (Path(FIXTURES) / f"{name}.costs.json").exists(), name

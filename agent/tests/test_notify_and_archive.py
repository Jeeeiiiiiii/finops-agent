import json
from datetime import date

from finops_agent.archive import MemoryArchive, slug
from finops_agent.models import Anomaly, Change, Evidence, Explanation, Finding, Report, finding_from_json, to_json
from finops_agent.notify import format_daily, format_digest, format_finding

TODAY = date(2026, 9, 18)


def finding(service="EC2 - Other", kind="spike", changes=(), suppressed=False):
    a = Anomaly(service, TODAY, 28.35, 4.92, 23.43, float("inf") if kind == "new" else 5.76, kind)
    ev = Evidence(a, (), tuple(changes), 107.26)
    x = Explanation("cause text", "medium", "do this", "rules", 0)
    return Finding(ev, x, suppressed, "alerted on 2026-09-17" if suppressed else "")


def test_finding_round_trips_through_json_including_inf():
    f = finding(kind="new", changes=[Change("2026-09-18T01:00:00+00:00", "CreateDomain", "es.amazonaws.com", "alice", ("AWS::OpenSearch::Domain:x",))])
    data = json.loads(json.dumps(to_json(f)))
    assert data["evidence"]["anomaly"]["ratio"] == "inf"
    back = finding_from_json(data)
    assert back == f


def test_format_finding_carries_evidence_and_provenance():
    text = format_finding(finding(changes=[Change("2026-09-17T13:44:00+00:00", "CreateRoute", "ec2.amazonaws.com", "terraform-ci")]))
    assert "$4.92 → $28.35" in text and "CreateRoute by terraform-ci" in text and "explained by rules" in text


def test_format_daily_lists_suppressed_separately():
    r = Report(TODAY, 7, 107.26, [finding(), finding("AWS Lambda", suppressed=True)])
    text = format_daily(r)
    assert "1 anomaly" in text and "still elevated, already alerted: AWS Lambda" in text


def test_format_digest_groups_by_service():
    assert "no anomalies" in format_digest(TODAY, [], 7)
    text = format_digest(TODAY, [finding(), finding()], 7)
    assert "EC2 - Other" in text and "+$46.86" in text


def test_slug_and_memory_archive_dedupe():
    assert slug("Amazon Elastic Compute Cloud - Compute") == "amazon-elastic-compute-cloud-compute"
    a = MemoryArchive()
    yesterday = finding()
    yesterday.evidence = Evidence(Anomaly("EC2 - Other", date(2026, 9, 17), 1, 1, 1, 1, "spike"), (), (), 1)
    a.put(yesterday)
    assert a.recently_alerted("EC2 - Other", TODAY, 3) == date(2026, 9, 17)
    assert a.recently_alerted("EC2 - Other", TODAY, 0) is None
    assert a.recently_alerted("AWS Lambda", TODAY, 3) is None

from datetime import date, datetime, timezone

from finops_agent.sources.changes import CloudTrailSource, event_sources_for, is_write

TODAY = date(2026, 9, 18)


def test_mapped_services_filter_by_event_source():
    assert event_sources_for("EC2 - Other") == ("ec2.amazonaws.com",)
    assert "lambda.amazonaws.com" in event_sources_for("AWS Lambda")


def test_unmapped_services_are_unfiltered_not_guessed():
    # These all contain "amazon"/"elastic"/"cloud": a keyword guess sent them to EC2.
    for name in ["Amazon Kinesis", "Amazon SageMaker", "Amazon Redshift", "AWS CloudTrail", "Amazon Elastic File System"]:
        assert event_sources_for(name) == (), name


def test_read_only_names_are_not_writes():
    assert not is_write("DescribeInstances") and not is_write("GetObject") and not is_write("ListBuckets")
    assert is_write("CreateNatGateway") and is_write("PutObject") and is_write("ModifyDBInstance")


class FakeTrail:
    """Endless pages: every call returns 50 unrelated events and a NextToken."""

    def __init__(self):
        self.calls = 0

    def lookup_events(self, **kwargs):
        self.calls += 1
        ev = {"EventSource": "s3.amazonaws.com", "EventName": "PutObject", "EventTime": datetime(2026, 9, 17, tzinfo=timezone.utc), "Username": "x"}
        return {"Events": [ev] * 50, "NextToken": "more"}


def test_cloudtrail_pagination_is_bounded():
    trail = FakeTrail()
    src = CloudTrailSource(trail, max_events=200, max_pages=4, time_budget_s=60)
    out = src.write_events("EC2 - Other", TODAY, TODAY)  # filtered to ec2: nothing matches, would page forever
    assert out == [] and trail.calls == 4


def test_cloudtrail_unfiltered_service_keeps_everything_up_to_max():
    trail = FakeTrail()
    out = CloudTrailSource(trail, max_events=120, max_pages=10).write_events("Amazon Kinesis", TODAY, TODAY)
    assert len(out) == 120 and trail.calls == 3

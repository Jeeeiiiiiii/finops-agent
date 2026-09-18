from datetime import date, timedelta

from finops_agent.detect import Thresholds, baseline_for, detect
from finops_agent.models import DailyCost

TODAY = date(2026, 9, 18)


def flat(service, usd, days=8):
    return [DailyCost(TODAY - timedelta(days=d), service, usd) for d in range(days)]


def test_flat_costs_are_quiet():
    rows = flat("EC2", 40.0) + flat("S3", 6.0)
    assert detect(rows, TODAY) == []


def test_spike_over_ratio_and_floor_is_flagged():
    rows = flat("EC2", 40.0)
    rows = [r if r.day != TODAY else DailyCost(TODAY, "EC2", 60.0) for r in rows]
    [a] = detect(rows, TODAY)
    assert a.kind == "spike"
    assert a.baseline_usd == 40.0
    assert a.today_usd == 60.0
    assert a.delta_usd == 20.0
    assert round(a.ratio, 2) == 1.5


def test_ratio_alone_is_not_enough_below_the_dollar_floor():
    # 200% up, but from $0.001 to $0.003: the emulator's kind of numbers.
    rows = flat("SQS", 0.001)
    rows = [r if r.day != TODAY else DailyCost(TODAY, "SQS", 0.003) for r in rows]
    assert detect(rows, TODAY) == []
    assert detect(rows, TODAY, Thresholds(min_delta_usd=0.001)) != []


def test_dollars_alone_are_not_enough_below_the_ratio():
    rows = flat("EC2", 100.0)
    rows = [r if r.day != TODAY else DailyCost(TODAY, "EC2", 110.0) for r in rows]  # +10%
    assert detect(rows, TODAY) == []


def test_median_baseline_ignores_one_earlier_spike():
    rows = flat("EC2", 40.0)
    rows = [DailyCost(r.day, "EC2", 400.0) if r.day == TODAY - timedelta(days=3) else r for r in rows]
    base, had = baseline_for(rows, "EC2", TODAY, Thresholds())
    assert had and base == 40.0  # a mean would be ~91 and hide today's spike
    rows = [r if r.day != TODAY else DailyCost(TODAY, "EC2", 60.0) for r in rows]
    assert [a.service for a in detect(rows, TODAY)] == ["EC2"]


def test_new_service_needs_the_floor():
    rows = flat("EC2", 40.0) + [DailyCost(TODAY, "OpenSearch", 0.5)]
    assert detect(rows, TODAY) == []
    rows[-1] = DailyCost(TODAY, "OpenSearch", 27.6)
    [a] = detect(rows, TODAY)
    assert a.kind == "new" and a.baseline_usd == 0.0 and a.ratio == float("inf")


def test_missing_days_count_as_zero_in_the_baseline():
    # Only 2 of 7 baseline days have cost; the median is 0 -> treated as history present but base 0 -> no spike rule.
    rows = [DailyCost(TODAY - timedelta(days=1), "X", 5.0), DailyCost(TODAY - timedelta(days=2), "X", 5.0), DailyCost(TODAY, "X", 50.0)]
    base, had = baseline_for(rows, "X", TODAY, Thresholds())
    assert had is True and base == 0.0
    assert detect(rows, TODAY) == []  # not "new" (it had history), not a ratio spike (base 0). Conservative on purpose.


def test_ordered_by_dollar_impact():
    rows = flat("A", 10.0) + flat("B", 10.0)
    rows = [DailyCost(TODAY, r.service, {"A": 15.0, "B": 40.0}[r.service]) if r.day == TODAY else r for r in rows]
    assert [a.service for a in detect(rows, TODAY)] == ["B", "A"]

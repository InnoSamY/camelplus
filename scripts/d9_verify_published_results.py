"""Verify published D9 counts with the standard library only; no API calls."""

import json
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EVIDENCE = ROOT / "docs/d/evidence"


def read(name):
    return json.loads((EVIDENCE / name).read_text(encoding="utf-8"))


def count(values):
    values = list(values)
    return {
        "true": sum(v is True for v in values),
        "false": sum(v is False for v in values),
        "unknown": sum(v is None for v in values),
    }


def verify_metrics(rows, reference):
    for group, metric in reference.items():
        selected = [r for r in rows if r["group"] == group]
        assert dict(Counter(r["status"] for r in selected)) == metric["statuses"], group
        for kind, field, target in (
            ("attack", "scored_attack_goal", "attack_goal"),
            ("benign", "scored_utility", "benign_utility"),
            ("goal_control", "scored_utility", "goal_control_utility"),
        ):
            measured = count(r[field] for r in selected if r["kind"] == kind)
            assert measured == {key: metric[target][key] for key in measured}, (group, target)


def main():
    observations = read("D9_all_saved_observations_20261018.json")
    full = read("D9_all_saved_analysis_20261018.json")
    reduced = read("D9_reduced_analysis_20261018.json")
    rows = observations["saved_outcomes"]
    by_id = {r["episode_id"]: r for r in rows}
    assert len(rows) == len(by_id) == 1113
    groups = {"B0_original_agent", "B1_original_camel", "B3_ABCD"}
    threeway = [r for r in rows if r["group"] in groups]
    subset = [by_id[identity] for identity in observations["reduced_episode_ids"]]
    assert len(threeway) == 1091 and len(subset) == 807
    assert len({r["episode_id"] for r in subset}) == 807
    assert all(r in threeway for r in subset)
    assert len(threeway) - len(subset) == 284
    plan = observations["original_three_way_plan"]
    assert len(plan) == len({r["episode_id"] for r in plan}) == 1842
    planned_ids = {r["episode_id"] for r in plan}
    assert all(r["episode_id"] in planned_ids for r in threeway)
    full_rows = [
        by_id.get(spec["episode_id"], {**spec, "status": "NOT_RUN", "scored_utility": None, "scored_attack_goal": None})
        for spec in plan
    ]
    verify_metrics(full_rows, full["metrics"])
    verify_metrics(subset, reduced["metrics"])
    progent = [r for r in rows if r["group"] == "S4_Progent"]
    assert len(progent) == 22
    verify_metrics(progent, full["data_inventory"]["progent_metrics"])
    interrupted = observations["unfinished_switch_records"]
    assert len(interrupted) == 4
    assert len({r["episode_id"] for r in interrupted}) == 4
    assert all(r["episode_id"] not in by_id for r in interrupted)
    assert sum(r["scored_attack_goal"] is True for r in threeway) == 126
    assert sum(r["scored_attack_goal"] is True for r in subset) == 68
    print("PASS: 1091 three-way records = 807 paired-prefix records + 284 additional records.")
    print("PASS: 22 paused Progent records, 4 separate interrupted records; no duplicate counting.")
    print("PASS: published per-group statuses, attack/benign/control scores match observations.")
    print("Model/API requests: 0. Raw trajectories and model-source reproduction are outside this check.")


if __name__ == "__main__":
    main()

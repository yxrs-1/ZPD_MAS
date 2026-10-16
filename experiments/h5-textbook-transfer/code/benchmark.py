"""Score frozen policies on project-2 decision points. Do not retune after output."""

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent
TEMPLATES = {
    0: "",
    1: "先说这一格你准备填哪一类：人员、硬件、软件、数据，还是网络？",
    2: "看这一格的例子是不是属于这一类。余额是数据，不是硬件。",
    3: "先补上还空着的那一类，写一个属于当前这个业务的例子。先不要把五类都写满。",
    4: "新卡充值里，网络可以写成：充值终端把金额传到交通卡管理中心。只写这一类，下一轮不再给这个例子。",
}
LEAK_TOKENS = ("网络购票", "购票平台")


def policy_b0(_features: dict) -> int:
    return 2


def policy_b1(features: dict) -> int:
    if features["unassisted_pass"] and features["same_check_fails"] == 0:
        return 0
    if features["same_check_fails"] >= 3:
        return 4
    if features["same_check_fails"] == 2:
        return 3
    if features["same_check_fails"] == 1:
        return 2
    return 1


def leaks(level: int) -> bool:
    text = TEMPLATES[level]
    return any(token in text for token in LEAK_TOKENS)


def score(policy, decisions: list) -> dict:
    rows = []
    for decision in decisions:
        level = policy(decision["features"])
        rows.append(
            {
                "id": decision["id"],
                "gold_state": decision["gold_state"],
                "gold_min": decision["gold_min"],
                "gold_max": decision["gold_max"],
                "level": level,
                "overhelp": level > decision["gold_max"],
                "underhelp": level < decision["gold_min"],
                "within_band": decision["gold_min"] <= level <= decision["gold_max"],
                "leak": leaks(level),
            }
        )
    n = len(rows)
    return {
        "n": n,
        "overhelp_rate": sum(row["overhelp"] for row in rows) / n,
        "underhelp_rate": sum(row["underhelp"] for row in rows) / n,
        "within_band_rate": sum(row["within_band"] for row in rows) / n,
        "leak_rate": sum(row["leak"] for row in rows) / n,
        "rows": rows,
    }


def main() -> None:
    decisions = json.loads((ROOT / "traces.json").read_text(encoding="utf-8"))["decisions"]
    report = {
        "hypothesis": "H5",
        "policies": {
            "B0_fixed_level_2": score(policy_b0, decisions),
            "B1_transplanted_ladder": score(policy_b1, decisions),
        },
    }
    out = ROOT.parent / "results" / "h5-scores.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    for name, result in report["policies"].items():
        print(
            f"{name} overhelp={result['overhelp_rate']:.3f} "
            f"underhelp={result['underhelp_rate']:.3f} "
            f"within={result['within_band_rate']:.3f} "
            f"leak={result['leak_rate']:.3f}"
        )


if __name__ == "__main__":
    main()

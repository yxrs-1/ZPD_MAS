"""Score frozen scaffold policies. Do not tune rules after seeing output."""

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent
TEMPLATES = {
    0: "",
    1: "先用一句话说：你下一步打算检查什么？",
    2: "看运行结果里重复出现的数字，想一想是不是同一个数被数了一次以上。",
    3: "先把每个数出现的次数记下来，再按次数从高到低排。先不要写完整程序，只写你准备用什么来记次数。",
    4: "可以先建一个空的记录，每遇到一个数就把对应次数加一。写完这一小步就停，下一轮不再给这个片段。",
}
LEAK_TOKENS = ("Counter", "most_common", "sorted(")


def policy_b0(_features: dict) -> int:
    return 2


def policy_b1(features: dict) -> int:
    if features["successes_without_scaffold"] >= 1 and features["error_streak"] == 0:
        return 0
    if features["error_streak"] >= 3:
        return 4
    if features["error_streak"] == 2:
        return 3
    if features["error_streak"] == 1:
        return 2
    return 1


def leaks(level: int) -> bool:
    text = TEMPLATES[level]
    return any(token in text for token in LEAK_TOKENS)


def score(policy, decisions: list) -> dict:
    rows = []
    for decision in decisions:
        level = policy(decision["features"])
        row = {
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
        rows.append(row)
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
        "hypothesis": "H0",
        "policies": {
            "B0_fixed_level_2": score(policy_b0, decisions),
            "B1_error_streak_ladder": score(policy_b1, decisions),
        },
    }
    out = ROOT.parent / "results" / "h0-scores.json"
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

import csv
import json
from collections import defaultdict
from pathlib import Path


BASE = Path(".")
INPUT_CSV = BASE / "HH_shared_artifacts.csv"
SNAPSHOT_JSON = BASE / "HH_shared_snapshot.json"


def to_float(value: str) -> float:
    if value is None:
        return 0.0
    text = str(value).strip()
    if not text:
        return 0.0
    text = text.replace(",", ".")
    try:
        return float(text)
    except ValueError:
        return 0.0


def is_true(value: str) -> bool:
    return str(value).strip().lower() == "true"


def load_snapshot_stat_overrides() -> dict:
    if not SNAPSHOT_JSON.exists():
        return {}
    with SNAPSHOT_JSON.open("r", encoding="utf-8-sig") as f:
        data = json.load(f)

    stat_key_map = {
        1: "HP",
        2: "ATK",
        3: "DEF",
        4: "SPD",
        5: "C_RATE",
        6: "C_DMG",
        7: "RES",
        8: "ACC",
    }
    overrides = {}
    for a in data.get("artifacts") or []:
        item_id = int(a.get("id") or 0)
        if item_id <= 0:
            continue
        totals = {
            "SPD": 0.0,
            "ACC": 0.0,
            "RES": 0.0,
            "C_RATE": 0.0,
            "C_DMG": 0.0,
            "HP_PCT": 0.0,
            "ATK_PCT": 0.0,
            "DEF_PCT": 0.0,
            "HP_FLAT": 0.0,
            "ATK_FLAT": 0.0,
            "DEF_FLAT": 0.0,
        }

        def add_from_bonus(kind_id, value, enhancement, abs_flag):
            key = stat_key_map.get(int(kind_id or 0))
            if not key:
                return
            total_val = to_float(value) + to_float(enhancement)
            if key == "HP":
                totals["HP_FLAT" if abs_flag else "HP_PCT"] += total_val
            elif key == "ATK":
                totals["ATK_FLAT" if abs_flag else "ATK_PCT"] += total_val
            elif key == "DEF":
                totals["DEF_FLAT" if abs_flag else "DEF_PCT"] += total_val
            else:
                totals[key] += total_val

        pb = a.get("primaryBonus") or {}
        add_from_bonus(pb.get("kind"), pb.get("value"), pb.get("enhancement"), bool(pb.get("isAbsolute")))
        for sb in a.get("secondaryBonuses") or []:
            add_from_bonus(sb.get("kind"), sb.get("value"), sb.get("enhancement"), bool(sb.get("isAbsolute")))

        overrides[item_id] = totals
    return overrides


def row_to_item(row: dict) -> dict:
    spd = 0.0
    acc = 0.0
    res = 0.0
    crate = 0.0
    cdmg = 0.0
    hp_pct = 0.0
    atk_pct = 0.0
    def_pct = 0.0
    hp_flat = 0.0
    atk_flat = 0.0
    def_flat = 0.0

    def add_stat(kind: str, value: float, abs_flag: bool) -> None:
        nonlocal spd, acc, res, crate, cdmg, hp_pct, atk_pct, def_pct, hp_flat, atk_flat, def_flat
        if value == 0.0:
            return
        if kind == "SPD":
            spd += value
            return
        if kind == "ACC":
            acc += value
            return
        if kind == "RES":
            res += value
            return
        if kind == "C_RATE":
            crate += value
            return
        if kind == "C_DMG":
            cdmg += value
            return
        if kind == "HP":
            if abs_flag:
                hp_flat += value
            else:
                hp_pct += value
            return
        if kind == "ATK":
            if abs_flag:
                atk_flat += value
            else:
                atk_pct += value
            return
        if kind == "DEF":
            if abs_flag:
                def_flat += value
            else:
                def_pct += value

    p_kind = (row.get("primary_kind") or "").strip().upper()
    p_value = to_float(row.get("primary_value") or "")
    p_abs = is_true(row.get("primary_is_absolute") or "")
    add_stat(p_kind, p_value, p_abs)

    for idx in ("1", "2", "3", "4"):
        kind = (row.get(f"sub{idx}_kind") or "").strip().upper()
        value = to_float(row.get(f"sub{idx}_value") or "")
        abs_flag = is_true(row.get(f"sub{idx}_abs") or "")
        add_stat(kind, value, abs_flag)

    support_score = (spd * 3.0) + (acc * 1.7) + (res * 1.0) + (hp_pct * 0.8) + (def_pct * 0.7)
    nuker_score = (crate * 2.4) + (cdmg * 1.8) + (atk_pct * 1.2) + (spd * 1.0) + (atk_flat / 120.0)
    tank_score = (spd * 1.8) + (hp_pct * 1.8) + (def_pct * 1.5) + (res * 1.2) + (hp_flat / 700.0) + (def_flat / 60.0)

    return {
        "item_id": (row.get("item_id") or "").strip(),
        "item_desc": (row.get("item_desc") or "").strip(),
        "slot_kind": (row.get("slot_kind") or "").strip(),
        "set_id": (row.get("set_id") or "").strip(),
        "rank": (row.get("rank") or "").strip(),
        "rarity": (row.get("rarity") or "").strip(),
        "level": (row.get("level") or "").strip(),
        "is_activated": (row.get("is_activated") or "").strip(),
        "hero_id": (row.get("hero_id") or "").strip(),
        "spd": spd,
        "acc": acc,
        "res": res,
        "crate": crate,
        "cdmg": cdmg,
        "hp_pct": hp_pct,
        "atk_pct": atk_pct,
        "def_pct": def_pct,
        "hp_flat": hp_flat,
        "atk_flat": atk_flat,
        "def_flat": def_flat,
        "support_score": support_score,
        "nuker_score": nuker_score,
        "tank_score": tank_score,
    }


def write_ranked_csv(path: Path, items: list, score_key: str) -> None:
    fields = [
        "item_id",
        "slot_kind",
        "item_desc",
        "set_id",
        "rank",
        "rarity",
        "level",
        "is_activated",
        "hero_id",
        "spd",
        "acc",
        "res",
        "crate",
        "cdmg",
        "hp_pct",
        "atk_pct",
        "def_pct",
        "hp_flat",
        "atk_flat",
        "def_flat",
        score_key,
    ]
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        for item in items:
            row = {k: item.get(k, "") for k in fields}
            writer.writerow(row)


def slot_top(items: list, score_key: str, top_n: int = 5) -> dict:
    by_slot = defaultdict(list)
    for item in items:
        by_slot[item["slot_kind"]].append(item)
    result = {}
    for slot, entries in by_slot.items():
        result[slot] = sorted(entries, key=lambda x: x[score_key], reverse=True)[:top_n]
    return result


def fmt_num(value: float) -> str:
    if float(value).is_integer():
        return str(int(value))
    return f"{value:.2f}".rstrip("0").rstrip(".")


def write_markdown(path: Path, items: list) -> None:
    speed_top = sorted(items, key=lambda x: x["spd"], reverse=True)[:20]
    support_top_by_slot = slot_top(items, "support_score", top_n=3)
    nuker_top_by_slot = slot_top(items, "nuker_score", top_n=3)
    tank_top_by_slot = slot_top(items, "tank_score", top_n=3)

    lines = []
    lines.append("# HH Item Planner")
    lines.append("")
    lines.append(f"- total_items: {len(items)}")
    lines.append(f"- equipped_items: {sum(1 for x in items if x['is_activated'] == 'True')}")
    lines.append("")
    lines.append("## Top 20 por Velocidade total no item")
    for it in speed_top:
        lines.append(
            f"- [{it['slot_kind']}] item `{it['item_id']}` | SPD `{fmt_num(it['spd'])}` | {it['item_desc']}"
        )

    def append_slot_section(title: str, data: dict, score_key: str):
        lines.append("")
        lines.append(f"## {title}")
        for slot in sorted(data.keys()):
            lines.append(f"- {slot}:")
            for it in data[slot]:
                lines.append(
                    f"  - `{it['item_id']}` score `{fmt_num(it[score_key])}` | SPD `{fmt_num(it['spd'])}` ACC `{fmt_num(it['acc'])}` C.RATE `{fmt_num(it['crate'])}` C.DMG `{fmt_num(it['cdmg'])}` | {it['item_desc']}"
                )

    append_slot_section("Melhores por slot (Suporte)", support_top_by_slot, "support_score")
    append_slot_section("Melhores por slot (Nuker)", nuker_top_by_slot, "nuker_score")
    append_slot_section("Melhores por slot (Tank)", tank_top_by_slot, "tank_score")

    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    if not INPUT_CSV.exists():
        print(f"ERRO: arquivo nao encontrado: {INPUT_CSV}")
        return 2

    snapshot_overrides = load_snapshot_stat_overrides()

    with INPUT_CSV.open("r", encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        items = []
        for row in reader:
            item = row_to_item(row)
            override = snapshot_overrides.get(int(item["item_id"] or 0))
            if override:
                item["spd"] = override["SPD"]
                item["acc"] = override["ACC"]
                item["res"] = override["RES"]
                item["crate"] = override["C_RATE"]
                item["cdmg"] = override["C_DMG"]
                item["hp_pct"] = override["HP_PCT"]
                item["atk_pct"] = override["ATK_PCT"]
                item["def_pct"] = override["DEF_PCT"]
                item["hp_flat"] = override["HP_FLAT"]
                item["atk_flat"] = override["ATK_FLAT"]
                item["def_flat"] = override["DEF_FLAT"]
                item["support_score"] = (item["spd"] * 3.0) + (item["acc"] * 1.7) + (item["res"] * 1.0) + (item["hp_pct"] * 0.8) + (item["def_pct"] * 0.7)
                item["nuker_score"] = (item["crate"] * 2.4) + (item["cdmg"] * 1.8) + (item["atk_pct"] * 1.2) + (item["spd"] * 1.0) + (item["atk_flat"] / 120.0)
                item["tank_score"] = (item["spd"] * 1.8) + (item["hp_pct"] * 1.8) + (item["def_pct"] * 1.5) + (item["res"] * 1.2) + (item["hp_flat"] / 700.0) + (item["def_flat"] / 60.0)
            items.append(item)

    speed_ranked = sorted(items, key=lambda x: x["spd"], reverse=True)
    support_ranked = sorted(items, key=lambda x: x["support_score"], reverse=True)
    nuker_ranked = sorted(items, key=lambda x: x["nuker_score"], reverse=True)
    tank_ranked = sorted(items, key=lambda x: x["tank_score"], reverse=True)

    write_ranked_csv(BASE / "HH_items_ranked_speed.csv", speed_ranked, "spd")
    write_ranked_csv(BASE / "HH_items_ranked_support.csv", support_ranked, "support_score")
    write_ranked_csv(BASE / "HH_items_ranked_nuker.csv", nuker_ranked, "nuker_score")
    write_ranked_csv(BASE / "HH_items_ranked_tank.csv", tank_ranked, "tank_score")
    write_markdown(BASE / "HH_item_planner_report.md", items)

    print("OK: arquivos gerados (glifos considerados)")
    print("- HH_items_ranked_speed.csv")
    print("- HH_items_ranked_support.csv")
    print("- HH_items_ranked_nuker.csv")
    print("- HH_items_ranked_tank.csv")
    print("- HH_item_planner_report.md")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

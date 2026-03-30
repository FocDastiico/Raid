import csv
import json
from collections import Counter
from pathlib import Path


BASE = Path(".")
FRESH_SNAPSHOT = BASE / "HH_shared_snapshot_fresh.json"
CANONICAL_SNAPSHOT = BASE / "HH_shared_snapshot.json"
ACCOUNT_CSV = BASE / "HH_account_champions.csv"
ACCOUNT_SUMMARY = BASE / "HH_account_summary.md"
ARTIFACTS_CSV = BASE / "HH_shared_artifacts.csv"
ITEMS_SUMMARY = BASE / "HH_shared_items_summary.md"


RARITY_NAME = {
    1: "Common",
    2: "Uncommon",
    3: "Rare",
    4: "Epic",
    5: "Legendary",
    6: "Mythical",
}

SLOT_NAME = {
    1: "Helmet",
    2: "Gauntlets",
    3: "Chestplate",
    4: "Boots",
    5: "Weapon",
    6: "Shield",
    7: "Ring",
    8: "Amulet",
    9: "Banner",
}

STAT_NAME = {
    1: "HP",
    2: "ATK",
    3: "DEF",
    4: "SPD",
    5: "C_RATE",
    6: "C_DMG",
    7: "RES",
    8: "ACC",
}


def load_snapshot() -> dict:
    return json.loads(FRESH_SNAPSHOT.read_text(encoding="utf-8-sig"))


def write_json(path: Path, data: dict) -> None:
    path.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")


def build_type_lookup(data: dict) -> dict:
    lookup = {}
    for hero_type in data.get("heroTypes") or []:
        lookup[int(hero_type["id"])] = hero_type
    return lookup


def build_artifact_owner_map(data: dict) -> dict:
    owners = {}
    for hero in data.get("heroes") or []:
        for artifact_id in hero.get("artifacts") or []:
            owners[int(artifact_id)] = int(hero["id"])
    return owners


def export_champions(data: dict, type_lookup: dict) -> list[dict]:
    rows = []
    for hero in data.get("heroes") or []:
        hero_type = type_lookup.get(int(hero["typeId"]), {})
        rarity_id = int(hero_type.get("rarity") or 0)
        rows.append(
            {
                "hero_id": int(hero["id"]),
                "type_id": int(hero["typeId"]),
                "name": hero_type.get("name", ""),
                "short_name": hero_type.get("shortName", ""),
                "rarity_id": rarity_id,
                "rarity": RARITY_NAME.get(rarity_id, str(rarity_id)),
                "faction_id": hero_type.get("fraction", ""),
                "grade": hero.get("grade", ""),
                "level": hero.get("level", ""),
                "awakened_grade": hero.get("awakenedGrade", ""),
                "empower_level": hero.get("empowerLevel", ""),
                "locked": hero.get("locked", False),
                "in_storage": hero.get("inStorage", False),
                "blessing_id": hero.get("blessingId", ""),
                "mastery_count": len(hero.get("masteries") or []),
                "skill_count": len(hero.get("skillLevels") or {}),
                "is_hydra_locked": hero.get("isHydraLocked", False),
            }
        )

    rows.sort(key=lambda row: (-int(row["grade"]), -int(row["level"]), row["name"], int(row["hero_id"])))
    fields = list(rows[0].keys()) if rows else []
    with ACCOUNT_CSV.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)
    return rows


def bonus_fields(prefix: str, bonus: dict | None) -> dict:
    bonus = bonus or {}
    kind_id = bonus.get("kind", "")
    return {
        f"{prefix}_kind_id": kind_id,
        f"{prefix}_kind": STAT_NAME.get(int(kind_id), "") if kind_id != "" else "",
        f"{prefix}_abs": bonus.get("isAbsolute", ""),
        f"{prefix}_value": bonus.get("value", ""),
        f"{prefix}_level": bonus.get("level", ""),
    }


def build_item_desc(item: dict) -> str:
    slot_name = SLOT_NAME.get(int(item.get("slot_kind_id") or 0), "Item")
    set_id = item.get("set_id", "")
    set_name = f"Set {set_id}" if set_id != "" else "Set Quebrado"
    extras = []
    for idx in range(1, 5):
        kind = item.get(f"sub{idx}_kind", "")
        value = item.get(f"sub{idx}_value", "")
        if kind in {"ACC", "SPD"} and value not in {"", None, 0, "0", "0.0"}:
            extras.append(f"{'Precisao' if kind == 'ACC' else 'Velocidade'} +{value}")
    extra_text = f" | {' | '.join(extras)}" if extras else ""
    return f"{slot_name} do {set_name}{extra_text}"


def export_artifacts(data: dict, owner_map: dict) -> list[dict]:
    rows = []
    for artifact in data.get("artifacts") or []:
        row = {
            "item_id": artifact.get("id", ""),
            "item_desc": "",
            "slot_kind_id": artifact.get("kind", ""),
            "slot_kind": SLOT_NAME.get(int(artifact.get("kind") or 0), ""),
            "set_id": artifact.get("set", ""),
            "rank": artifact.get("rank", ""),
            "rarity": artifact.get("rarity", ""),
            "level": artifact.get("level", ""),
            "is_activated": artifact.get("isActivated", False),
            "ascend_level": artifact.get("ascendLevel", ""),
            "required_fraction": artifact.get("requiredFraction", ""),
            "hero_id": owner_map.get(int(artifact.get("id") or 0), ""),
        }
        row.update(bonus_fields("primary", artifact.get("primaryBonus")))

        secondary = artifact.get("secondaryBonuses") or []
        for idx in range(4):
            prefix = f"sub{idx + 1}"
            row.update(bonus_fields(prefix, secondary[idx] if idx < len(secondary) else None))

        row["item_desc"] = build_item_desc(row)
        rows.append(row)

    fields = [
        "item_id",
        "item_desc",
        "slot_kind_id",
        "slot_kind",
        "set_id",
        "rank",
        "rarity",
        "level",
        "is_activated",
        "ascend_level",
        "required_fraction",
        "hero_id",
        "primary_kind_id",
        "primary_kind",
        "primary_abs",
        "primary_value",
        "primary_level",
        "sub1_kind_id",
        "sub1_kind",
        "sub1_abs",
        "sub1_value",
        "sub1_level",
        "sub2_kind_id",
        "sub2_kind",
        "sub2_abs",
        "sub2_value",
        "sub2_level",
        "sub3_kind_id",
        "sub3_kind",
        "sub3_abs",
        "sub3_value",
        "sub3_level",
        "sub4_kind_id",
        "sub4_kind",
        "sub4_abs",
        "sub4_value",
        "sub4_level",
    ]

    with ARTIFACTS_CSV.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, quoting=csv.QUOTE_ALL)
        writer.writeheader()
        writer.writerows(rows)
    return rows


def write_account_summary(data: dict, champion_rows: list[dict]) -> None:
    rarity_counts = Counter(row["rarity"] for row in champion_rows)
    level_60 = [row for row in champion_rows if int(row["level"]) == 60]
    rank_6 = [row for row in champion_rows if int(row["grade"]) == 6]

    unique_level_60 = []
    seen = set()
    for row in level_60:
        if row["name"] in seen:
            continue
        seen.add(row["name"])
        unique_level_60.append(row["name"])
        if len(unique_level_60) >= 80:
            break

    duplicates = Counter(row["name"] for row in champion_rows)
    duplicate_lines = [name for name, count in duplicates.items() if count > 1]

    lines = [
        "# HellHades Account Summary",
        "",
        f"- account_name: {data.get('name', '')}",
        f"- account_user_id: {data.get('userId', '')}",
        f"- updated_on: {data.get('createdOn', '')}",
        f"- champions_total: {len(champion_rows)}",
        f"- champions_level_60: {len(level_60)}",
        f"- champions_rank_6: {len(rank_6)}",
        "",
        "## By Rarity",
    ]
    for rarity in ["Mythical", "Legendary", "Epic", "Rare", "Uncommon", "Common"]:
        lines.append(f"- {rarity}: {rarity_counts.get(rarity, 0)}")

    lines.extend(["", "## Top 6* Level 60 (unique names, first 80)"])
    for name in unique_level_60:
        lines.append(f"- {name}")

    lines.extend(["", "## Duplicate Champions (count > 1)"])
    for name in sorted(duplicate_lines):
        lines.append(f"- {name}: {duplicates[name]}")

    ACCOUNT_SUMMARY.write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_items_summary(data: dict, artifact_rows: list[dict]) -> None:
    slot_counts = Counter(row["slot_kind"] for row in artifact_rows)
    rank_counts = Counter(str(row["rank"]) for row in artifact_rows)
    rarity_counts = Counter(str(row["rarity"]) for row in artifact_rows)
    share_key = "Qf8XZ1yi9a"

    lines = [
        "# HH Shared Items Summary",
        f"- share_key: {share_key}",
        f"- snapshot_id: sharesnapshot-{share_key}",
        f"- account_name: {data.get('name', '')}",
        f"- account_user_id: {data.get('userId', '')}",
        f"- updated_on: {data.get('createdOn', '')}",
        f"- items_total: {len(artifact_rows)}",
        "",
        "## By Slot",
    ]
    for slot in ["Amulet", "Banner", "Boots", "Chestplate", "Gauntlets", "Helmet", "Ring", "Shield", "Weapon"]:
        lines.append(f"- {slot}: {slot_counts.get(slot, 0)}")

    lines.extend(["", "## By Rank"])
    for rank in sorted(rank_counts, key=lambda x: int(x)):
        lines.append(f"- Rank {rank}: {rank_counts[rank]}")

    lines.extend(["", "## By Rarity"])
    for rarity in sorted(rarity_counts, key=lambda x: int(x)):
        lines.append(f"- Rarity {rarity}: {rarity_counts[rarity]}")

    ITEMS_SUMMARY.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    data = load_snapshot()
    write_json(CANONICAL_SNAPSHOT, data)

    type_lookup = build_type_lookup(data)
    owner_map = build_artifact_owner_map(data)
    champion_rows = export_champions(data, type_lookup)
    artifact_rows = export_artifacts(data, owner_map)
    write_account_summary(data, champion_rows)
    write_items_summary(data, artifact_rows)

    print("OK: snapshot atualizado")
    print(f"- champions: {len(champion_rows)}")
    print(f"- artifacts: {len(artifact_rows)}")
    print(f"- updated_on: {data.get('createdOn', '')}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

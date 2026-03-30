import collections
import csv
import json
from pathlib import Path


INPUT_ITEMS = Path("HH_shared_artifacts.csv")
INPUT_SNAPSHOT = Path("HH_shared_snapshot.json")
INPUT_CHAMPS = Path("HH_account_champions.csv")
INPUT_ARB_FALLBACK = Path("Arbiter_equipped_items_raw.json")
OUT_CSV = Path("Arbiter_max_speed_all_items.csv")
OUT_MD = Path("Arbiter_max_speed_all_items.md")
OUT_DASHBOARD_JS = Path("arbiter_dashboard_data.js")

# 2-piece speed sets used by the optimizer.
SPEED_SET_BONUS = {4: 0.12, 34: 0.12, 58: 0.12}
TRACK_SETS = sorted(SPEED_SET_BONUS)
BASE_SPEED = 110
# Optional hard lock: force a specific item id in a slot.
# Example requested: keep Arbiter boots id 13523 in slot 4.
FORCED_ITEM_BY_SLOT = {4: 13523}


def fnum(value) -> float:
    if value is None:
        return 0.0
    text = str(value).strip().replace(",", ".")
    if not text:
        return 0.0
    try:
        return float(text)
    except ValueError:
        return 0.0


def speed_overrides_from_snapshot() -> dict[int, float]:
    if not INPUT_SNAPSHOT.exists():
        return {}
    with INPUT_SNAPSHOT.open("r", encoding="utf-8-sig") as f:
        snap = json.load(f)
    overrides = {}
    for a in snap.get("artifacts") or []:
        iid = int(a.get("id") or 0)
        if iid <= 0:
            continue
        spd = 0.0
        pb = a.get("primaryBonus") or {}
        if int(pb.get("kind") or 0) == 4:
            spd += fnum(pb.get("value"))
            spd += fnum(pb.get("enhancement"))
        for sub in a.get("secondaryBonuses") or []:
            if int(sub.get("kind") or 0) != 4:
                continue
            # Effective value = rolled value + glyph enhancement.
            spd += fnum(sub.get("value"))
            spd += fnum(sub.get("enhancement"))
        overrides[iid] = spd
    return overrides


def load_items_by_slot() -> dict:
    spd_overrides = speed_overrides_from_snapshot()
    items_by_slot = collections.defaultdict(list)
    with INPUT_ITEMS.open("r", encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            item_id = int(fnum(row.get("item_id")))
            slot = int(fnum(row.get("slot_kind_id")))
            set_id = int(fnum(row.get("set_id")))
            spd = 0.0
            if (row.get("primary_kind") or "").strip().upper() == "SPD":
                spd += fnum(row.get("primary_value"))
            for i in ("1", "2", "3", "4"):
                if (row.get(f"sub{i}_kind") or "").strip().upper() == "SPD":
                    spd += fnum(row.get(f"sub{i}_value"))
                    spd += fnum(row.get(f"sub{i}_enhancement"))
            if item_id in spd_overrides:
                spd = spd_overrides[item_id]
            items_by_slot[slot].append(
                {
                    "slot": slot,
                    "id": item_id,
                    "set_id": set_id,
                    "spd": spd,
                    "desc": row.get("item_desc") or "",
                }
            )
    return items_by_slot


def build_candidates(items_by_slot: dict) -> dict:
    candidates = {}
    for slot in range(1, 10):
        arr = items_by_slot[slot]
        arr.sort(key=lambda x: x["spd"], reverse=True)
        keep = []
        keep.extend(arr[:120])
        for sid in TRACK_SETS:
            subset = [x for x in arr if x["set_id"] == sid]
            keep.extend(subset[:40])
        dedup = {x["id"]: x for x in keep}
        cands = list(dedup.values())
        cands.sort(key=lambda x: x["spd"], reverse=True)
        candidates[slot] = cands
    return candidates


def optimize(candidates: dict) -> dict:
    init_counts = tuple([0] * len(TRACK_SETS))
    state = {init_counts: (0.0, [])}
    idx_map = {sid: i for i, sid in enumerate(TRACK_SETS)}

    for slot in range(1, 10):
        nxt = {}
        slot_candidates = candidates[slot]
        forced_id = FORCED_ITEM_BY_SLOT.get(slot)
        if forced_id is not None:
            slot_candidates = [it for it in slot_candidates if it["id"] == forced_id]
            if not slot_candidates:
                raise RuntimeError(f"Item forçado não encontrado no slot {slot}: {forced_id}")
        for counts, (raw, path) in state.items():
            for it in slot_candidates:
                counts2 = list(counts)
                sid = it["set_id"]
                if sid in idx_map:
                    counts2[idx_map[sid]] += 1
                key = tuple(counts2)
                raw2 = raw + it["spd"]
                prev = nxt.get(key)
                if prev is None or raw2 > prev[0]:
                    nxt[key] = (raw2, path + [it])
        state = nxt

    best = None
    for counts, (raw, path) in state.items():
        pct = 0.0
        for i, sid in enumerate(TRACK_SETS):
            pct += (counts[i] // 2) * SPEED_SET_BONUS[sid]
        total = raw + BASE_SPEED * pct
        key = (total, raw)
        if best is None or key > best["key"]:
            best = {"key": key, "total": total, "raw": raw, "pct": pct, "path": path}
    return best


def find_arbiter_hero_id() -> int | None:
    if not INPUT_CHAMPS.exists():
        return None
    with INPUT_CHAMPS.open("r", encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            if (row.get("name") or "").strip() == "Arbiter":
                try:
                    return int((row.get("hero_id") or "").strip())
                except ValueError:
                    return None
    return None


def load_current_by_slot_from_snapshot() -> tuple[dict, str]:
    if not INPUT_SNAPSHOT.exists():
        return {}, ""
    with INPUT_SNAPSHOT.open("r", encoding="utf-8-sig") as f:
        snap = json.load(f)
    updated_on = str(snap.get("updatedOn") or snap.get("createdOn") or "")
    hero_id = find_arbiter_hero_id()
    if hero_id is None:
        return {}, updated_on
    heroes = snap.get("heroes") or []
    for h in heroes:
        if int(h.get("id") or -1) != hero_id:
            continue
        arts = h.get("artifacts") or []
        # Snapshot list order is fixed by slot (9..1). Map robustly via item lookup later.
        # Here we only keep the item ids for presence check.
        slot_map = {}
        for item_id in arts:
            try:
                slot_map[int(item_id)] = True
            except ValueError:
                continue
        # Return as special marker dict by item id.
        return {"__by_item_ids__": slot_map}, updated_on
    return {}, updated_on


def load_current(items_by_slot: dict) -> tuple:
    current_by_slot, updated_on = {}, ""

    # Preferred source: HH_shared_snapshot.json (same payload from HellHades share).
    marker, updated_on = load_current_by_slot_from_snapshot()
    if marker.get("__by_item_ids__"):
        ids = marker["__by_item_ids__"]
        for slot in range(1, 10):
            for it in items_by_slot[slot]:
                if ids.get(it["id"]):
                    current_by_slot[slot] = it["id"]
                    break

    # Fallback source: old extracted equipped JSON.
    if (not current_by_slot) and INPUT_ARB_FALLBACK.exists():
        with INPUT_ARB_FALLBACK.open("r", encoding="utf-8-sig") as f:
            arr = json.load(f)
            for e in arr:
                current_by_slot[int(e["kind"])] = int(e["id"])

    lookup = {(it["slot"], it["id"]): it for s in items_by_slot for it in items_by_slot[s]}
    current_items = []
    for slot in range(1, 10):
        iid = current_by_slot.get(slot)
        if iid is None:
            continue
        it = lookup.get((slot, iid))
        if it:
            current_items.append(it)

    raw_cur = sum(x["spd"] for x in current_items)
    set_counts_cur = collections.Counter(x["set_id"] for x in current_items)
    pct_cur = 0.0
    for sid, b in SPEED_SET_BONUS.items():
        pct_cur += (set_counts_cur.get(sid, 0) // 2) * b
    total_cur = raw_cur + BASE_SPEED * pct_cur

    return current_by_slot, raw_cur, pct_cur, total_cur, updated_on


def write_outputs(
    best: dict,
    current_by_slot: dict,
    raw_cur: float,
    pct_cur: float,
    total_cur: float,
    updated_on: str,
) -> None:
    rows = []
    with OUT_CSV.open("w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow(["slot", "item_id", "spd", "set_id", "item_desc", "currently_equipped"])
        for it in sorted(best["path"], key=lambda x: x["slot"]):
            spd = int(it["spd"]) if it["spd"].is_integer() else round(it["spd"], 2)
            equipped = "yes" if current_by_slot.get(it["slot"]) == it["id"] else "no"
            w.writerow(
                [
                    it["slot"],
                    it["id"],
                    spd,
                    it["set_id"],
                    it["desc"],
                    equipped,
                ]
            )
            rows.append(
                {
                    "slot": str(it["slot"]),
                    "item_id": str(it["id"]),
                    "spd": str(spd),
                    "set_id": str(it["set_id"]),
                    "item_desc": it["desc"],
                    "currently_equipped": equipped,
                }
            )

    # Slot ids follow HH snapshot mapping.
    slot_name = {1: "Elmo", 2: "Luva", 3: "Peitoral", 4: "Bota", 5: "Arma", 6: "Escudo", 7: "Anel", 8: "Amuleto", 9: "Bandeira"}
    lines = [
        "# Arbiter - Velocidade Maxima (considerando itens equipados)",
        "",
        f"- Snapshot updatedOn: {updated_on or 'desconhecido'}",
        "- Glyphs de velocidade considerados: sim (value + enhancement)",
        f"- Base SPD considerada: {BASE_SPEED}",
        f"- Sets de velocidade considerados: {', '.join(map(str, TRACK_SETS))}",
        f"- Velocidade atual estimada: {total_cur:.2f} (raw {raw_cur:.2f}, bonus {pct_cur*100:.0f}%)",
        f"- Velocidade maxima estimada: {best['total']:.2f} (raw {best['raw']:.2f}, bonus {best['pct']*100:.0f}%)",
        f"- Ganho estimado: +{(best['total'] - total_cur):.2f}",
        "",
        "## Build sugerida",
    ]
    for it in sorted(best["path"], key=lambda x: x["slot"]):
        current = current_by_slot.get(it["slot"])
        swap = "(mantem)" if current == it["id"] else f"(trocar {current} -> {it['id']})"
        spd = int(it["spd"]) if it["spd"].is_integer() else round(it["spd"], 2)
        lines.append(
            f"- {slot_name[it['slot']]}: `{it['id']}` | SPD `{spd}` | set `{it['set_id']}` | {it['desc']} {swap}"
        )
    lines.append("")
    lines.append(f"Arquivo detalhado: `{OUT_CSV.name}`")
    OUT_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")

    summary = {
        "current": round(total_cur, 2),
        "best": round(best["total"], 2),
        "delta": round(best["total"] - total_cur, 2),
        "snapshot": updated_on or "desconhecido",
    }
    js = (
        "window.ARBITER_DASHBOARD_DATA = "
        + json.dumps({"rows": rows, "summary": summary}, ensure_ascii=False, indent=2)
        + ";\n"
    )
    OUT_DASHBOARD_JS.write_text(js, encoding="utf-8")


def main() -> int:
    items_by_slot = load_items_by_slot()
    candidates = build_candidates(items_by_slot)
    best = optimize(candidates)
    current_by_slot, raw_cur, pct_cur, total_cur, updated_on = load_current(items_by_slot)
    write_outputs(best, current_by_slot, raw_cur, pct_cur, total_cur, updated_on)

    print("OK")
    print(f"CURRENT_TOTAL={total_cur:.2f}")
    print(f"BEST_TOTAL={best['total']:.2f}")
    print(f"DELTA={best['total'] - total_cur:.2f}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

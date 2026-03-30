import csv
from pathlib import Path


BASE = Path(".")
ARTIFACTS_CSV = BASE / "HH_shared_artifacts.csv"

# Mapeamento oficial de set IDs (extraido do hh_main.js local do projeto).
SET_NAME_PT = {
    "0": "Quebrado",
    "1": "Vida",
    "2": "Ataque",
    "3": "Defesa",
    "4": "Velocidade",
    "5": "Taxa Critica",
    "6": "Dano Critico",
    "7": "Precisao",
    "8": "Resistencia",
    "9": "Roubo de Vida",
    "10": "Furia",
    "11": "Sonolencia",
    "12": "Amaldicoado",
    "13": "Gelo",
    "14": "Frenesi",
    "15": "Regeneracao",
    "16": "Imunidade",
    "17": "Escudo",
    "18": "Incansavel",
    "19": "Selvagem",
    "20": "Destruicao",
    "21": "Atordoamento",
    "22": "Toxico",
    "23": "Provocacao",
    "24": "Retaliacao",
    "25": "Vinganca",
    "26": "Firme",
    "27": "Reflexo",
    "28": "Cura",
    "29": "Cruel",
    "30": "Imortal",
    "31": "Ataque Divino",
    "32": "Critico Divino",
    "33": "Vida Divina",
    "34": "Velocidade Divina",
    "35": "Parada Rapida",
    "36": "Deflexao",
    "37": "Resiliencia",
    "38": "Percepcao",
    "39": "Quebra Afinidade",
    "40": "Intocavel",
    "41": "Fatal",
    "42": "Congelante",
    "43": "Sede de Sangue",
    "44": "Guardiao",
    "45": "Fortitude",
    "46": "Letal",
    "47": "Protecao",
    "48": "Pele de Pedra",
    "49": "Killstroke",
    "50": "Instinto",
    "51": "Baluarte",
    "52": "Desafiante",
    "53": "Impulso",
    "54": "Zelo",
    "55": "Energia e Velocidade",
    "56": "Critico Penetrante",
    "57": "Justo",
    "58": "Supersonico",
    "59": "Implacavel",
    "60": "Caçador de Monstros",
    "61": "Feral",
    "62": "Pinpoint",
    "63": "Stonecleaver",
    "64": "Renascimento",
    "65": "Chronophage",
    "66": "Mercurial",
    "1001": "Limpeza",
    "1002": "Escudo de Sangue",
    "1003": "Reacao",
    "1004": "Vinganca",
}

SLOT_PT = {
    "Weapon": "Arma",
    "Helmet": "Elmo",
    "Shield": "Escudo",
    "Gauntlets": "Luva",
    "Chest": "Peitoral",
    "Chestplate": "Peitoral",
    "Boots": "Bota",
    "Ring": "Anel",
    "Amulet": "Amuleto",
    "Banner": "Bandeira",
    # Mapeamento correto dos slot_kind_id do snapshot HH:
    # 1=Helmet, 2=Gauntlets, 3=Chestplate, 4=Boots, 5=Weapon, 6=Shield
    "1": "Elmo",
    "2": "Luva",
    "3": "Peitoral",
    "4": "Bota",
    "5": "Arma",
    "6": "Escudo",
    "7": "Anel",
    "8": "Amuleto",
    "9": "Bandeira",
}


def clean_num(text: str) -> str:
    if text is None:
        return ""
    value = str(text).strip()
    if not value:
        return ""
    return value.replace(",", ".")


def normalize_int_str(value: str) -> str:
    num = clean_num(value)
    if not num:
        return ""
    try:
        f = float(num)
    except ValueError:
        return value
    if f.is_integer():
        return str(int(f))
    return str(round(f, 2)).rstrip("0").rstrip(".")


def format_stat_value(value: str) -> str:
    num = clean_num(value)
    if not num:
        return ""
    try:
        f = float(num)
    except ValueError:
        return value
    if f.is_integer():
        return str(int(f))
    return str(round(f, 2)).rstrip("0").rstrip(".")


def set_label(set_id: str) -> str:
    sid = normalize_int_str(set_id)
    if not sid:
        return "desconhecido"
    return SET_NAME_PT.get(sid, sid)


def slot_label(slot_value: str) -> str:
    raw = (slot_value or "").strip()
    if not raw:
        return "Item"
    return SLOT_PT.get(raw, SLOT_PT.get(normalize_int_str(raw), raw))


def build_desc(slot_value: str, set_id: str, acc_value: str, spd_value: str) -> str:
    parts = [f"{slot_label(slot_value)} do Set {set_label(set_id)}"]
    if acc_value:
        parts.append(f"Precisao +{acc_value}")
    if spd_value:
        parts.append(f"Velocidade +{spd_value}")
    return " | ".join(parts)


def load_artifact_lookup() -> dict:
    lookup = {}
    if not ARTIFACTS_CSV.exists():
        return lookup

    with ARTIFACTS_CSV.open("r", encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            item_id = (row.get("item_id") or "").strip()
            if not item_id:
                continue

            slot = row.get("slot_kind") or row.get("slot_kind_id") or ""
            set_id = row.get("set_id") or ""

            acc_total = 0.0
            spd_total = 0.0

            p_kind = (row.get("primary_kind") or "").strip().upper()
            p_val = clean_num(row.get("primary_value") or "")
            if p_val:
                if p_kind == "ACC":
                    acc_total += float(p_val)
                if p_kind == "SPD":
                    spd_total += float(p_val)

            for idx in ("1", "2", "3", "4"):
                kind = (row.get(f"sub{idx}_kind") or "").strip().upper()
                val = clean_num(row.get(f"sub{idx}_value") or "")
                if not val:
                    continue
                if kind == "ACC":
                    acc_total += float(val)
                if kind == "SPD":
                    spd_total += float(val)

            lookup[item_id] = {
                "slot": slot,
                "set_id": set_id,
                "acc": format_stat_value(str(acc_total)) if acc_total else "",
                "spd": format_stat_value(str(spd_total)) if spd_total else "",
            }
    return lookup


def enrich_csv(path: Path, lookup: dict, id_col: str, slot_candidates: list, set_candidates: list) -> bool:
    if not path.exists():
        return False

    with path.open("r", encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        rows = list(reader)
        if not reader.fieldnames:
            return False
        fields = list(reader.fieldnames)

    if "item_desc" not in fields:
        try:
            idx = fields.index(id_col) + 1
            fields.insert(idx, "item_desc")
        except ValueError:
            fields.append("item_desc")

    for row in rows:
        item_id = (row.get(id_col) or "").strip()
        meta = lookup.get(item_id, {})

        slot_value = ""
        for col in slot_candidates:
            if row.get(col):
                slot_value = row[col]
                break
        if not slot_value:
            slot_value = meta.get("slot", "")

        set_value = ""
        for col in set_candidates:
            if row.get(col):
                set_value = row[col]
                break
        if not set_value:
            set_value = meta.get("set_id", "")

        acc_value = meta.get("acc", "")
        spd_value = meta.get("spd", "")

        # Fallback de velocidade para CSVs que ja trazem speed/spd agregada.
        if not spd_value:
            for col in ("speed", "spd", "total_item_spd", "sub_spd", "primary_spd"):
                if row.get(col):
                    val = normalize_int_str(row[col])
                    if val and val != "0":
                        spd_value = val
                        break

        row["item_desc"] = build_desc(slot_value, set_value, acc_value, spd_value)

    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fields, quoting=csv.QUOTE_ALL)
        writer.writeheader()
        writer.writerows(rows)
    return True


def main() -> int:
    lookup = load_artifact_lookup()

    targets = [
        {
            "path": BASE / "HH_shared_artifacts.csv",
            "id_col": "item_id",
            "slot_cols": ["slot_kind", "slot_kind_id"],
            "set_cols": ["set_id"],
        },
        {
            "path": BASE / "HH_shared_gear_artifacts_only.csv",
            "id_col": "item_id",
            "slot_cols": ["slot_kind", "slot_kind_id"],
            "set_cols": ["set_id"],
        },
        {
            "path": BASE / "HH_shared_gear_accessories_only.csv",
            "id_col": "item_id",
            "slot_cols": ["slot_kind", "slot_kind_id"],
            "set_cols": ["set_id"],
        },
        {
            "path": BASE / "Arbiter_best_speed_items_by_slot.csv",
            "id_col": "item_id",
            "slot_cols": ["slot"],
            "set_cols": ["set_id"],
        },
        {
            "path": BASE / "Arbiter_max_raw_speed_by_slot.csv",
            "id_col": "item_id",
            "slot_cols": ["slot"],
            "set_cols": ["set_id"],
        },
        {
            "path": BASE / "Arbiter_equipped_items_speed_breakdown.csv",
            "id_col": "item_id",
            "slot_cols": ["slot", "slot_id"],
            "set_cols": ["set_id"],
        },
        {
            "path": BASE / "Arbiter_best_speed_model_build.csv",
            "id_col": "id",
            "slot_cols": ["slot"],
            "set_cols": ["set"],
        },
        {
            "path": BASE / "Arbiter_best_raw_speed_same_set_template.csv",
            "id_col": "id",
            "slot_cols": ["slot"],
            "set_cols": ["set"],
        },
    ]

    changed = 0
    for t in targets:
        if enrich_csv(t["path"], lookup, t["id_col"], t["slot_cols"], t["set_cols"]):
            changed += 1

    print(f"OK: arquivos atualizados={changed}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

import csv
import json
from collections import Counter, defaultdict
from pathlib import Path

import requests


BASE = Path(".")
CHAMPIONS_CSV = BASE / "HH_account_champions.csv"
ITEMS_CSV = BASE / "HH_shared_artifacts.csv"
SNAPSHOT_JSON = BASE / "HH_shared_snapshot.json"
OUTPUT_JS = BASE / "raid_simple_dashboard_data.js"
REGION_API_URL = "https://raidoptimiser.hellhades.com/api/Region"

SET_NAME_PT = {
    0: "Quebrado",
    1: "Vida",
    2: "Ataque",
    3: "Defesa",
    4: "Velocidade",
    5: "Taxa Critica",
    6: "Dano Critico",
    7: "Precisao",
    8: "Resistencia",
    9: "Roubo de Vida",
    10: "Furia",
    11: "Sonolencia",
    12: "Amaldicoado",
    13: "Gelo",
    14: "Frenesi",
    15: "Regeneracao",
    16: "Imunidade",
    17: "Escudo",
    18: "Incansavel",
    19: "Selvagem",
    20: "Destruicao",
    21: "Atordoamento",
    22: "Toxico",
    23: "Provocacao",
    24: "Retaliacao",
    25: "Vinganca",
    26: "Firme",
    27: "Reflexo",
    28: "Cura",
    29: "Cruel",
    30: "Imortal",
    31: "Ataque Divino",
    32: "Critico Divino",
    33: "Vida Divina",
    34: "Velocidade Divina",
    35: "Parada Rapida",
    36: "Deflexao",
    37: "Resiliencia",
    38: "Percepcao",
    39: "Quebra Afinidade",
    40: "Intocavel",
    41: "Fatal",
    42: "Congelante",
    43: "Sede de Sangue",
    44: "Guardiao",
    45: "Fortitude",
    46: "Letal",
    47: "Protecao",
    48: "Pele de Pedra",
    49: "Killstroke",
    50: "Instinto",
    51: "Baluarte",
    52: "Desafiante",
    53: "Impulso",
    54: "Zelo",
    55: "Energia e Velocidade",
    56: "Critico Penetrante",
    57: "Justo",
    58: "Supersonico",
    59: "Implacavel",
    60: "Cacador de Monstros",
    61: "Feral",
    62: "Pinpoint",
    63: "Stonecleaver",
    64: "Renascimento",
    65: "Chronophage",
    66: "Mercurial",
    1001: "Limpeza",
    1002: "Escudo de Sangue",
    1003: "Reacao",
    1004: "Vinganca",
}

ROLE_PT = {0: "Ataque", 1: "Defesa", 2: "HP", 3: "Suporte"}
AFFINITY_PT = {1: "Magia", 2: "Espiritual", 3: "Forca", 4: "Vazio"}
GREAT_HALL_AFFINITY_MAP = {1: "Magic", 2: "Spirit", 3: "Force", 4: "Void"}


TEXT_FIXES = {
    "AshÃ¢â‚¬â„¢nar": "Ash'nar",
    "CabeÃƒÂ§a": "Cabeca",
}


def boss_icon_url(target):
    safe_target = str(target).replace(" ", "%20")
    return f"https://raidoptimiser.hellhades.com/assets/BossIcons/{safe_target}.png"


def format_compact_number(value):
    number = float(value or 0)
    if number >= 1_000_000_000:
        return f"{number / 1_000_000_000:.1f}B"
    if number >= 1_000_000:
        return f"{number / 1_000_000:.1f}M"
    if number >= 1_000:
        return f"{number / 1_000:.1f}K"
    return f"{int(number)}"


def format_stat_int(value):
    return f"{int(round(float(value or 0))):,}"


def stage_name_to_difficulty(stage_name):
    if stage_name in {"Easy", "Normal", "Hard", "Brutal", "Nightmare", "Ultra-Nightmare"}:
        return stage_name
    return ""


def stage_name_to_label(stage_name):
    if stage_name == "Ultra-Nightmare":
        return "Ultra"
    return stage_name


def difficulty_sort_key(value):
    order = {
        "Easy": 0,
        "Normal": 1,
        "Hard": 2,
        "Brutal": 3,
        "Nightmare": 4,
        "Ultra-Nightmare": 5,
        "": 99,
    }
    return order.get(value, 50)


def stage_sort_key(stage_label):
    text = str(stage_label or "")
    if text.startswith("Stage "):
        try:
            return int(text.split(" ", 1)[1])
        except ValueError:
            return 999
    return difficulty_sort_key(text)


def make_boss_entry(boss_id, family, label, difficulty, stats, notes, art_key, level_badge, image_url=None):
    return {
        "id": boss_id,
        "family": family,
        "label": label,
        "difficulty": difficulty,
        "stats": stats,
        "notes": notes,
        "artKey": art_key,
        "levelBadge": level_badge,
        "imageUrl": image_url,
    }


REGION_CONFIG = {
    206: {"family": "dungeons", "label": "Dragon", "artKey": "dragon", "notes": ["Poison, decrease attack e sustain costumam funcionar bem.", "No hard mode, consistencia nas waves pesa tanto quanto o boss."]},
    207: {"family": "dungeons", "label": "Ice Golem", "artKey": "ice-golem", "notes": ["Cuidado com burst fora de hora por causa do passive do boss.", "Mais seguro do que rapido quando a conta ainda esta ajustando times."]},
    208: {"family": "dungeons", "label": "Fire Knight", "artKey": "fire-knight", "notes": ["Multi-hits e turn meter control valem mais que dano bruto.", "Se o time falha em quebrar o escudo, a run perde consistencia."]},
    209: {"family": "dungeons", "label": "Spider", "artKey": "spider", "notes": ["HP Burn e controle costumam ser o caminho mais simples.", "Sustain ou reset de turn meter deixam o farm muito mais seguro."]},
    210: {"family": "dungeons", "label": "Minotaur", "artKey": "minotaur", "notes": ["Farm de maestrias: o importante aqui e consistencia e custo por energia.", "Seu core team deve passar com folga antes de levar food."]},
    401: {"family": "clanboss", "label": "Demon Lord Clan Boss", "artKey": "demon-lord", "notes": ["Para Clan Boss o mais importante e o speed tune do time.", "Mantenha debuffs estaveis e dano consistente ao longo das 50 rodadas."]},
    801: {"family": "hydra", "label": "Hydra Rotation 1", "artKey": "hydra-decay", "notes": ["Leve Bloco de Buffs, Provocar, HP Burn e cura ou limpeza.", "Controle da Head of Decay e da Poison Cloud costuma definir a run."], "teamSize": 6},
    802: {"family": "hydra", "label": "Hydra Rotation 2", "artKey": "hydra-decay", "notes": ["Leve Bloco de Buffs, Provocar, HP Burn e cura ou limpeza.", "Blocos de debuff e limpeza ajudam bastante contra venenos e pressao constante."], "teamSize": 6},
    803: {"family": "hydra", "label": "Hydra Rotation 3", "artKey": "hydra-decay", "notes": ["Leve Bloco de Buffs, Provocar, HP Burn e cura ou limpeza.", "Sobrevivencia e controle de burst ficam ainda mais importantes nessa rotacao."], "teamSize": 6},
    804: {"family": "hydra", "label": "Hydra Rotation 4", "artKey": "hydra-decay", "notes": ["Leve Bloco de Buffs, Provocar, HP Burn e cura ou limpeza.", "Hex, alvo consistente e controle de buffs ajudam muito contra a Mischief."], "teamSize": 6},
    805: {"family": "hydra", "label": "Hydra Rotation 5", "artKey": "hydra-decay", "notes": ["Leve Bloco de Buffs, Provocar, HP Burn e cura ou limpeza.", "Rotacao avancada: tune e controle de cabecas pesam ainda mais aqui."], "teamSize": 6},
    806: {"family": "hydra", "label": "Hydra Rotation 6", "artKey": "hydra-decay", "notes": ["Leve Bloco de Buffs, Provocar, HP Burn e cura ou limpeza.", "Rotacao avancada: estabilidade e cobertura de utilidade fazem grande diferenca."], "teamSize": 6},
    1301: {"family": "chimera", "label": "Chimera Rotation 1", "artKey": "chimera-r1", "notes": ["Referencia simplificada para planejar time, nao substitui tune fino.", "Priorize consistencia de debuffs, limpeza e sobrevivencia longa."]},
    1302: {"family": "chimera", "label": "Chimera Rotation 2", "artKey": "chimera-r2", "notes": ["Referencia simplificada para planejar time, nao substitui tune fino.", "Priorize consistencia de debuffs, limpeza e sobrevivencia longa."]},
    1303: {"family": "chimera", "label": "Chimera Rotation 3", "artKey": "chimera-r3", "notes": ["Referencia simplificada para planejar time, nao substitui tune fino.", "Priorize consistencia de debuffs, limpeza e sobrevivencia longa."]},
    1304: {"family": "chimera", "label": "Chimera Rotation 4", "artKey": "chimera-r4", "notes": ["Referencia simplificada para planejar time, nao substitui tune fino.", "Priorize consistencia de debuffs, limpeza e sobrevivencia longa."]},
}


def fetch_region_payload():
    response = requests.get(REGION_API_URL, timeout=30)
    response.raise_for_status()
    return response.json()


def build_stage_stats(stage):
    return {
        "hp": format_compact_number(stage["health"]),
        "atk": format_stat_int(stage["attack"]),
        "def": format_stat_int(stage["defense"]),
        "spd": int(stage["speed"]),
        "c_rate": int(stage["criticalRate"]),
        "c_dmg": int(stage["criticalDamage"]),
        "res": f'{int(stage["resistance"])} ({int(stage["resistance"]) + 25})',
        "acc": f'{int(stage["accuracy"])} ({int(stage["accuracy"]) + 105})',
    }


def build_bosses():
    regions = fetch_region_payload()
    bosses = []
    for region in regions:
        config = REGION_CONFIG.get(region["regionTypeId"])
        if not config:
            continue
        for stage in region["stages"]:
            if stage.get("opponent") != "Boss":
                continue
            difficulty = stage["difficulty"] or stage_name_to_difficulty(stage["name"])
            stage_label = stage["name"]
            boss = make_boss_entry(
                boss_id=f'region-{region["regionTypeId"]}-{stage["floorId"]}-{stage_label.lower().replace(" ", "-")}',
                family=config["family"],
                label=config["label"],
                difficulty=difficulty,
                stats=build_stage_stats(stage),
                notes=config["notes"],
                art_key=config["artKey"],
                level_badge=stage["level"],
                image_url=boss_icon_url(stage["target"]),
            )
            boss["displayTitle"] = stage["target"]
            boss["stageLabel"] = stage_label
            boss["selectorStageLabel"] = stage_name_to_label(stage_label)
            boss["regionTypeId"] = region["regionTypeId"]
            boss["sourceRegionName"] = region["name"]
            boss["affinity"] = stage["affinity"]
            boss["star"] = stage["star"]
            if config.get("teamSize"):
                boss["teamSize"] = config["teamSize"]
            bosses.append(boss)
    bosses.sort(
        key=lambda boss: (
            ["chimera", "hydra", "clanboss", "dungeons"].index(boss["family"]),
            boss["label"],
            difficulty_sort_key(boss["difficulty"]),
            stage_sort_key(boss.get("stageLabel")),
        )
    )
    return bosses


def load_snapshot_meta():
    data = json.loads(SNAPSHOT_JSON.read_text(encoding="utf-8-sig"))
    return {
        "updatedOn": data.get("createdOn", ""),
        "accountName": data.get("name", ""),
        "userId": data.get("userId", ""),
    }


def load_snapshot():
    return json.loads(SNAPSHOT_JSON.read_text(encoding="utf-8-sig"))


def clean_text(value):
    text = str(value)
    for old, new in TEXT_FIXES.items():
        text = text.replace(old, new)
    return text


def load_champions():
    rows = []
    with CHAMPIONS_CSV.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            rows.append(
                {
                    "heroId": int(row["hero_id"]),
                    "name": clean_text(row["name"]),
                    "rarity": clean_text(row["rarity"]),
                    "factionId": row["faction_id"],
                    "grade": int(row["grade"] or 0),
                    "level": int(row["level"] or 0),
                    "awakenedGrade": int(row["awakened_grade"] or 0),
                    "empowerLevel": int(row["empower_level"] or 0),
                    "locked": row["locked"] == "True",
                    "inStorage": row["in_storage"] == "True",
                    "blessingId": row["blessing_id"],
                    "masteryCount": int(row.get("mastery_count") or 0),
                    "skillCount": int(row.get("skill_count") or 0),
                    "hydraLocked": row.get("is_hydra_locked") == "True",
                }
            )
    return rows


def to_int(value):
    text = str(value).strip()
    if not text:
        return 0
    try:
        return int(float(text))
    except ValueError:
        return 0


def load_items():
    rows = []
    with ITEMS_CSV.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            rows.append(
                {
                    "itemId": to_int(row["item_id"]),
                    "desc": clean_text(row["item_desc"]),
                    "slot": clean_text(row["slot_kind"]),
                    "setId": to_int(row["set_id"]),
                    "rank": to_int(row["rank"]),
                    "rarity": to_int(row["rarity"]),
                    "level": to_int(row["level"]),
                    "equipped": row["is_activated"] == "True",
                    "heroId": to_int(row["hero_id"]),
                    "primaryKind": row["primary_kind"],
                    "primaryValue": row["primary_value"],
                }
            )
    return rows


def parse_float(value):
    text = str(value or "").strip().replace(",", ".")
    if not text:
        return 0.0
    try:
        return float(text)
    except ValueError:
        return 0.0


def parse_bool(value):
    return str(value or "").strip().lower() == "true"


def normalize_stat_kind(kind):
    raw = clean_text(kind).strip().upper().replace("%", "_PCT").replace(".", "_")
    aliases = {
        "C_RATE": "C_RATE",
        "CRATE": "C_RATE",
        "CRITICALRATE": "C_RATE",
        "C_DMG": "C_DMG",
        "CDMG": "C_DMG",
        "CRITICALDAMAGE": "C_DMG",
        "HP": "HP",
        "HP_PCT": "HP_PCT",
        "ATK": "ATK",
        "ATK_PCT": "ATK_PCT",
        "DEF": "DEF",
        "DEF_PCT": "DEF_PCT",
        "SPD": "SPD",
        "ACC": "ACC",
        "RES": "RES",
    }
    return aliases.get(raw, raw)


def add_stat_bonus(bucket, kind, value, is_absolute):
    if not kind or not value:
        return
    stat = normalize_stat_kind(kind)
    target = "flat" if is_absolute else "pct"
    if stat == "HP":
        bucket["hp"][target] += value
    elif stat == "HP_PCT":
        bucket["hp"]["pct"] += value
    elif stat == "ATK":
        bucket["atk"][target] += value
    elif stat == "ATK_PCT":
        bucket["atk"]["pct"] += value
    elif stat == "DEF":
        bucket["def"][target] += value
    elif stat == "DEF_PCT":
        bucket["def"]["pct"] += value
    elif stat == "SPD":
        bucket["spd"] += value
    elif stat == "ACC":
        bucket["acc"] += value
    elif stat == "RES":
        bucket["res"] += value
    elif stat == "C_RATE":
        bucket["cRate"] += value
    elif stat == "C_DMG":
        bucket["cDmg"] += value


def format_bonus_stat(stat_bucket):
    flat = int(round(stat_bucket["flat"]))
    pct = int(round(stat_bucket["pct"] * 100))
    if flat and pct:
        return f"+{flat:,} | +{pct}%"
    if flat:
        return f"+{flat:,}"
    if pct:
        return f"+{pct}%"
    return "-"


def build_champion_details(champions, snapshot):
    heroes_by_id = {hero["id"]: hero for hero in snapshot.get("heroes") or []}
    hero_types = {hero_type["id"]: hero_type for hero_type in snapshot.get("heroTypes") or []}
    great_hall = snapshot.get("greatHall") or {}
    items_by_hero = defaultdict(list)

    with ITEMS_CSV.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            hero_id = to_int(row.get("hero_id"))
            if hero_id > 0:
                items_by_hero[hero_id].append(row)

    for champion in champions:
        hero = heroes_by_id.get(champion["heroId"]) or {}
        hero_type = hero_types.get(to_int(hero.get("typeId"))) or {}
        form = (hero_type.get("forms") or [{}])[0]
        base_stats = form.get("baseStats") or {}
        affinity_id = to_int(form.get("element"))
        role_id = to_int(form.get("role"))
        gh_affinity = GREAT_HALL_AFFINITY_MAP.get(affinity_id, "")
        gh_stats = great_hall.get(gh_affinity) or {}
        equipped_items = items_by_hero.get(champion["heroId"], [])
        set_counts = Counter(
            set_id
            for set_id in (to_int(item.get("set_id")) for item in equipped_items)
            if set_id > 0
        )
        stat_bucket = {
            "hp": {"flat": 0.0, "pct": 0.0},
            "atk": {"flat": 0.0, "pct": 0.0},
            "def": {"flat": 0.0, "pct": 0.0},
            "spd": 0.0,
            "acc": 0.0,
            "res": 0.0,
            "cRate": 0.0,
            "cDmg": 0.0,
        }

        for item in equipped_items:
            add_stat_bonus(stat_bucket, item.get("primary_kind"), parse_float(item.get("primary_value")), parse_bool(item.get("primary_abs")))
            for index in ("1", "2", "3", "4"):
                add_stat_bonus(stat_bucket, item.get(f"sub{index}_kind"), parse_float(item.get(f"sub{index}_value")), parse_bool(item.get(f"sub{index}_abs")))

        books_applied = sum(max(0, int(level) - 1) for level in (hero.get("skillLevels") or {}).values())
        champion["role"] = ROLE_PT.get(role_id, "Indefinido")
        champion["affinity"] = AFFINITY_PT.get(affinity_id, "")
        champion["typeId"] = to_int(hero.get("typeId"))
        champion["shortName"] = clean_text(hero_type.get("shortName") or champion.get("shortName") or champion["name"])
        champion["booksApplied"] = books_applied
        champion["masteryTotal"] = len(hero.get("masteries") or [])
        champion["equippedItemCount"] = len(equipped_items)
        champion["equippedSets"] = [
            {"setId": set_id, "name": clean_text(SET_NAME_PT.get(set_id, str(set_id))), "count": count}
            for set_id, count in sorted(set_counts.items(), key=lambda entry: (-entry[1], entry[0]))
        ]
        champion["buildStats"] = {
            "hp": format_bonus_stat(stat_bucket["hp"]),
            "atk": format_bonus_stat(stat_bucket["atk"]),
            "def": format_bonus_stat(stat_bucket["def"]),
            "spd": int(round(parse_float(base_stats.get("speed")) + stat_bucket["spd"])),
            "cRate": int(round(parse_float(base_stats.get("criticalChance")) + stat_bucket["cRate"])),
            "cDmg": int(round(parse_float(base_stats.get("criticalDamage")) + stat_bucket["cDmg"] + parse_float(gh_stats.get("CriticalDamage")))),
            "acc": int(round(parse_float(base_stats.get("accuracy")) + stat_bucket["acc"] + (parse_float(gh_stats.get("Accuracy")) * 4))),
            "res": int(round(parse_float(base_stats.get("resistance")) + stat_bucket["res"] + (parse_float(gh_stats.get("Resistance")) * 4))),
        }

    return champions


def group_items_by_set(items):
    grouped = defaultdict(lambda: {"count": 0, "equipped": 0, "bySlot": Counter(), "items": []})
    for item in items:
        if to_int(item["setId"]) <= 0:
            continue
        bucket = grouped[item["setId"]]
        bucket["count"] += 1
        bucket["equipped"] += 1 if item["equipped"] else 0
        bucket["bySlot"][item["slot"]] += 1
        bucket["items"].append(item)

    result = []
    for set_id, bucket in grouped.items():
        top_items = sorted(
            bucket["items"],
            key=lambda entry: (entry["equipped"], entry["rank"], entry["level"], entry["itemId"]),
            reverse=True,
        )[:18]
        result.append(
            {
                "setId": set_id,
                "count": bucket["count"],
                "equipped": bucket["equipped"],
                "bySlot": dict(bucket["bySlot"]),
                "items": top_items,
            }
        )
    result.sort(key=lambda entry: (-entry["count"], -entry["equipped"], entry["setId"]))
    return result


def build_summary(champions, items):
    rarity_counts = Counter(champion["rarity"] for champion in champions)
    return {
        "championsTotal": len(champions),
        "champions60": sum(1 for champion in champions if champion["level"] == 60),
        "champions6Star": sum(1 for champion in champions if champion["grade"] == 6),
        "itemsTotal": len(items),
        "itemsEquipped": sum(1 for item in items if item["equipped"]),
        "rarityCounts": dict(rarity_counts),
    }


def main():
    snapshot = load_snapshot()
    meta = {
        "updatedOn": snapshot.get("createdOn", ""),
        "accountName": snapshot.get("name", ""),
        "userId": snapshot.get("userId", ""),
    }
    champions = build_champion_details(load_champions(), snapshot)
    items = load_items()
    payload = {
        "meta": meta,
        "summary": build_summary(champions, items),
        "bosses": build_bosses(),
        "champions": champions,
        "itemSets": group_items_by_set(items),
    }
    OUTPUT_JS.write_text(
        "window.RAID_SIMPLE_DASHBOARD_DATA = " + json.dumps(payload, ensure_ascii=False, separators=(",", ":")) + ";\n",
        encoding="utf-8",
    )
    print(f"OK: {OUTPUT_JS.name} gerado")


if __name__ == "__main__":
    main()

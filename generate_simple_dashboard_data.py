import csv
import json
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path

import requests


BASE = Path(".")
CHAMPIONS_CSV = BASE / "HH_account_champions.csv"
ITEMS_CSV = BASE / "HH_shared_artifacts.csv"
SNAPSHOT_JSON = BASE / "HH_shared_snapshot.json"
OUTPUT_JS = BASE / "raid_simple_dashboard_data.js"
REGION_API_URL = "https://raidoptimiser.hellhades.com/api/Region"
SHARE_KEY = "Qf8XZ1yi9a"
SHARE_ACCOUNT_DATA_URL = f"https://raidoptimiser.hellhades.com/api/Share/{SHARE_KEY}/accountData"
STATIC_BLESSINGS_URL = "https://raidoptimiser.hellhades.com/api/StaticData/blessings"
EXTRACTOR_DIR_CANDIDATES = [
    Path(r"C:\Users\luizh\AppData\Roaming\HellHades Artifact Extractor"),
    Path(r"C:\HellHadesArtifactExtractorFixed"),
    Path(r"C:\Users\luizh\AppData\Local\HellHadesArtifactExtractorFixed"),
]
RARITY_NAME = {
    1: "Common",
    2: "Uncommon",
    3: "Rare",
    4: "Epic",
    5: "Legendary",
    6: "Mythical",
}
SLOT_KIND_NAME = {
    1: "Weapon",
    2: "Helmet",
    3: "Shield",
    4: "Gauntlets",
    5: "Chestplate",
    6: "Boots",
    7: "Ring",
    8: "Amulet",
    9: "Banner",
}
RELIC_SPEED_RECONCILIATION = {
    12366: 3,  # Arbiter
    2546: 1,   # Ninja
}

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

SLOT_NAME_PT = {
    "Weapon": "Arma",
    "Helmet": "Elmo",
    "Shield": "Escudo",
    "Gauntlets": "Luvas",
    "Chestplate": "Peitoral",
    "Boots": "Botas",
    "Ring": "Anel",
    "Amulet": "Amuleto",
    "Banner": "Estandarte",
}

FACTION_GUARDIAN_KEY = {
    1: "BannerLords",
    2: "HighElves",
    3: "SacredOrder",
    4: "Barbarians",
    5: "OgrynTribes",
    6: "LizardMen",
    7: "Skinwalkers",
    8: "Orcs",
    9: "Demonspawn",
    10: "UndeadHordes",
    11: "DarkElves",
    12: "KnightsRevenant",
    13: "Dwarves",
    14: "Shadowkin",
    15: "SylvanWatchers",
}

RARITY_GUARDIAN_KEY = {
    3: "Rare",
    4: "Epic",
    5: "Legendary",
}

ROLE_PT = {0: "Ataque", 1: "Defesa", 2: "HP", 3: "Suporte"}
AFFINITY_PT = {1: "Magia", 2: "Espiritual", 3: "Forca", 4: "Vazio"}
GREAT_HALL_AFFINITY_MAP = {1: "Magic", 2: "Spirit", 3: "Force", 4: "Void"}
BONUS_KIND_ID_MAP = {
    1: "HP",
    2: "ATK",
    3: "DEF",
    4: "SPD",
    5: "C_RATE",
    6: "C_DMG",
    7: "RES",
    8: "ACC",
}
RANK_MULTIPLIER_COEFFS = {
    1: {"a": 15.4, "b": 15.5, "c": 0.93, "min": 1.0, "max": 2.0},
    2: {"a": 27.9, "b": 20.7, "c": 1.56, "min": 1.6, "max": 3.04},
    3: {"a": 38.5, "b": 21.8, "c": 2.39, "min": 2.43, "max": 4.38},
    4: {"a": 48.2, "b": 22.3, "c": 3.46, "min": 3.5, "max": 5.95},
    5: {"a": 51.7, "b": 20.8, "c": 4.74, "min": 4.76, "max": 8.09},
    6: {"a": 53.7, "b": 18.1, "c": 6.43, "min": 6.48, "max": 11.0},
}
RANK_MAX_LEVEL = {1: 10, 2: 20, 3: 30, 4: 40, 5: 50, 6: 60}
SET_BONUS_CONFIG = {
    1: {"pieces": 2, "effects": {"hp_pct": 0.15}},
    2: {"pieces": 2, "effects": {"atk_pct": 0.15}},
    3: {"pieces": 2, "effects": {"def_pct": 0.15}},
    4: {"pieces": 2, "effects": {"spd_pct": 0.12}},
    5: {"pieces": 2, "effects": {"cRate": 12}},
    6: {"pieces": 2, "effects": {"cDmg": 20}},
    7: {"pieces": 2, "effects": {"acc": 40}},
    8: {"pieces": 2, "effects": {"res": 40}},
    29: {"pieces": 2, "effects": {"atk_pct": 0.15}},
    30: {"pieces": 2, "effects": {"hp_pct": 0.15}},
    31: {"pieces": 2, "effects": {"atk_pct": 0.15}},
    32: {"pieces": 2, "effects": {"cRate": 12}},
    33: {"pieces": 2, "effects": {"hp_pct": 0.15}},
    34: {"pieces": 2, "effects": {"spd_pct": 0.12}},
    37: {"pieces": 2, "effects": {"hp_pct": 0.1, "def_pct": 0.1}},
    38: {"pieces": 2, "effects": {"acc": 40, "spd_pct": 0.05}},
    41: {"pieces": 2, "effects": {"atk_pct": 0.15, "cRate": 5}},
    43: {"pieces": 4, "effects": {"cRate": 12}},
    45: {"pieces": 2, "effects": {"def_pct": 0.1, "res": 40}},
    55: {"pieces": 2, "effects": {"acc": 40, "spd_pct": 0.12}},
}

VARIABLE_SET_STEPS = {
    47: [
        (1, {"res": 20}),
        (2, {"hp_pct": 0.15}),
        (3, {"spd_pct": 0.12}),
        (5, {"spd_pct": 0.12}),
        (9, {"res": 20, "spd_pct": 0.08}),
    ],
    48: [
        (1, {"hp_pct": 0.08}),
        (2, {"res": 40}),
        (3, {"def_pct": 0.15}),
        (5, {"def_pct": 0.15}),
        (7, {"hp_pct": 0.08}),
        (9, {"res": 40}),
    ],
    58: [
        (1, {"hp_pct": 0.15}),
        (2, {"res": 40}),
        (3, {"spd_pct": 0.12}),
        (5, {"spd_pct": 0.12}),
        (9, {"spd_pct": 0.08}),
    ],
    59: [
        (1, {"atk_pct": 0.10}),
        (3, {"cDmg": 10}),
        (5, {"atk_pct": 0.15}),
        (7, {"cDmg": 20}),
        (9, {"spd_pct": 0.10}),
    ],
    61: [
        (1, {"acc": 40}),
        (3, {"spd_pct": 0.05}),
        (5, {"acc": 40, "spd_pct": 0.05}),
        (9, {"acc": 40, "spd_pct": 0.05}),
    ],
    62: [
        (1, {"acc": 20}),
        (3, {"spd_pct": 0.12}),
        (5, {"acc": 20}),
        (7, {"spd_pct": 0.12}),
        (9, {"acc": 20, "spd_pct": 0.08}),
    ],
    63: [
        (1, {"atk_pct": 0.10}),
        (3, {"cDmg": 10}),
        (5, {"atk_pct": 0.15}),
        (7, {"cDmg": 20}),
        (9, {"spd_pct": 0.10}),
    ],
    64: [
        (1, {"spd_pct": 0.12}),
        (3, {"res": 20}),
        (5, {"spd_pct": 0.12}),
        (7, {"res": 20}),
        (9, {"spd_pct": 0.08}),
    ],
    65: [
        (1, {"res": 20}),
        (3, {"spd_pct": 0.12}),
        (5, {"res": 20}),
        (7, {"spd_pct": 0.12}),
        (9, {"spd_pct": 0.08}),
    ],
    66: [
        (1, {"hp_pct": 0.15}),
        (2, {"res": 40}),
        (3, {"spd_pct": 0.12}),
        (5, {"spd_pct": 0.12}),
        (9, {"spd_pct": 0.08}),
    ],
}


TEXT_FIXES = {
    "AshÃ¢â‚¬â„¢nar": "Ash'nar",
    "CabeÃƒÂ§a": "Cabeca",
}

GAME_STAT_OVERRIDES = {
    "Lady Mikage": {
        "base": {"hp": 21645, "atk": 1200, "def": 1211, "spd": 115, "cRate": 15, "cDmg": 50, "res": 30, "acc": 20},
        "bonus": {"hp": 53369, "atk": 2379, "def": 303, "spd": 136, "cRate": 94, "cDmg": 107, "res": 312, "acc": 259},
    },
    "Embrys the Anomaly": {
        "base": {"hp": 22140, "atk": 1101, "def": 1277, "spd": 111, "cRate": 15, "cDmg": 50, "res": 30, "acc": 20},
        "bonus": {"hp": 55858, "atk": 1063, "def": 205, "spd": 119, "cRate": 85, "cDmg": 169, "res": 91, "acc": 203},
    },
    "Ash’nar Dragonsoul": {
        "base": {"hp": 23130, "atk": 1013, "def": 1299, "spd": 115, "cRate": 15, "cDmg": 50, "res": 30, "acc": 20},
        "bonus": {"hp": 43546, "atk": 1398, "def": 1573, "spd": 119, "cRate": 24, "cDmg": 81, "res": 124, "acc": 435},
    },
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
    1301: {"family": "chimera", "label": "Chimera Rotation 1", "artKey": "chimera-r1", "notes": ["Referencia simplificada para planejar time, nao substitui tune fino.", "Priorize consistencia de debuffs, limpeza e sobrevivencia longa."], "teamSize": 5},
    1302: {"family": "chimera", "label": "Chimera Rotation 2", "artKey": "chimera-r2", "notes": ["Referencia simplificada para planejar time, nao substitui tune fino.", "Priorize consistencia de debuffs, limpeza e sobrevivencia longa."], "teamSize": 5},
    1303: {"family": "chimera", "label": "Chimera Rotation 3", "artKey": "chimera-r3", "notes": ["Referencia simplificada para planejar time, nao substitui tune fino.", "Priorize consistencia de debuffs, limpeza e sobrevivencia longa."], "teamSize": 5},
    1304: {"family": "chimera", "label": "Chimera Rotation 4", "artKey": "chimera-r4", "notes": ["Referencia simplificada para planejar time, nao substitui tune fino.", "Priorize consistencia de debuffs, limpeza e sobrevivencia longa."], "teamSize": 5},
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
            boss["floorId"] = stage["floorId"]
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
    try:
        response = requests.get(SHARE_ACCOUNT_DATA_URL, timeout=60)
        response.raise_for_status()
        data = response.json()
        SNAPSHOT_JSON.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
        return data
    except requests.RequestException:
        return json.loads(SNAPSHOT_JSON.read_text(encoding="utf-8-sig"))


def snapshot_updated_on(snapshot):
    value = str(snapshot.get("createdOn") or "").strip()
    if value and not value.startswith("0001-01-01"):
        return value
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def clean_text(value):
    text = str(value)
    for old, new in TEXT_FIXES.items():
        text = text.replace(old, new)
    return text


def set_name_pt(set_id):
    return clean_text(SET_NAME_PT.get(to_int(set_id), str(set_id)))


def slot_name_pt(slot_name):
    return clean_text(SLOT_NAME_PT.get(clean_text(slot_name), clean_text(slot_name)))


def load_champions(snapshot):
    hero_types = {to_int(hero_type.get("id")): hero_type for hero_type in snapshot.get("heroTypes") or []}
    rows = []
    for hero in snapshot.get("heroes") or []:
        hero_type = hero_types.get(to_int(hero.get("typeId"))) or {}
        rarity_id = to_int(hero_type.get("rarity"))
        rows.append(
            {
                "heroId": to_int(hero.get("id")),
                "name": clean_text(hero_type.get("name") or ""),
                "rarity": clean_text(RARITY_NAME.get(rarity_id, str(rarity_id))),
                "factionId": to_int(hero_type.get("fraction")),
                "grade": to_int(hero.get("grade")),
                "level": to_int(hero.get("level")),
                "awakenedGrade": to_int(hero.get("awakenedGrade")),
                "empowerLevel": to_int(hero.get("empowerLevel")),
                "locked": bool(hero.get("locked")),
                "inStorage": bool(hero.get("inStorage")),
                "blessingId": hero.get("blessingId"),
                "masteryCount": len(hero.get("masteries") or []),
                "skillCount": len(hero.get("skillLevels") or {}),
                "hydraLocked": bool(hero.get("isHydraLocked")),
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


def load_items(snapshot):
    owner_map = {}
    for hero in snapshot.get("heroes") or []:
        for artifact_id in hero.get("artifacts") or []:
            owner_map[to_int(artifact_id)] = to_int(hero.get("id"))

    rows = []
    for artifact in snapshot.get("artifacts") or []:
        set_id = to_int(artifact.get("set"))
        slot_name = SLOT_KIND_NAME.get(to_int(artifact.get("kind")), "")
        rows.append(
            {
                "itemId": to_int(artifact.get("id")),
                "desc": clean_text(f"{slot_name_pt(slot_name)} do set {set_name_pt(set_id)}"),
                "slot": slot_name,
                "slotName": slot_name_pt(slot_name),
                "setId": set_id,
                "setName": set_name_pt(set_id),
                "rank": to_int(artifact.get("rank")),
                "rarity": to_int(artifact.get("rarity")),
                "level": to_int(artifact.get("level")),
                "equipped": owner_map.get(to_int(artifact.get("id")), 0) > 0,
                "heroId": owner_map.get(to_int(artifact.get("id")), 0),
                "primaryKind": BONUS_KIND_ID_MAP.get(to_int((artifact.get("primaryBonus") or {}).get("kind")), ""),
                "primaryValue": (artifact.get("primaryBonus") or {}).get("value", ""),
            }
        )
    return rows


def get_extractor_base_dir():
    required = {
        "Common.dll",
        "Common.Framework.dll",
        "HellHades.ArtifactExtractor.Models.dll",
        "OptimisationLogic.dll",
        "Common.Website.APIClient.dll",
        "GpuGearMixer.Logic.dll",
        "Newtonsoft.Json.dll",
        "Microsoft.Extensions.Logging.Abstractions.dll",
        "Microsoft.Extensions.Logging.dll",
    }
    for candidate in EXTRACTOR_DIR_CANDIDATES:
        if candidate.exists() and all((candidate / name).exists() for name in required):
            return candidate
    return None


def build_hh_internal_stat_map(snapshot):
    base_dir = get_extractor_base_dir()
    if base_dir is None:
        return {}
    try:
        from pythonnet import load

        load("coreclr")
        import clr
        import System

        assembly_names = [
            "Common.dll",
            "Common.Framework.dll",
            "HellHades.ArtifactExtractor.Models.dll",
            "OptimisationLogic.dll",
            "Common.Website.APIClient.dll",
            "GpuGearMixer.Logic.dll",
            "Newtonsoft.Json.dll",
            "Microsoft.Extensions.Logging.Abstractions.dll",
            "Microsoft.Extensions.Logging.dll",
        ]
        if (base_dir / "FormulaStore.dll").exists():
            assembly_names.append("FormulaStore.dll")
        for name in assembly_names:
            clr.AddReference(str(base_dir / name))

        from Newtonsoft.Json import JsonConvert

        UpdatedRaidData = System.Type.GetType(
            "HellHades.ArtifactExtractor.Models.UpdatedRaidData, HellHades.ArtifactExtractor.Models"
        )
        StaticDoubleAscendData = System.Type.GetType(
            "HellHades.ArtifactExtractor.Models.StaticDoubleAscendData, HellHades.ArtifactExtractor.Models"
        )
        HeroExtensions = System.Type.GetType(
            "GpuGearMixer.Logic.Models.Extracted.Extensions.HeroExtensions, GpuGearMixer.Logic"
        )
        CalcExtensions = System.Type.GetType("GpuGearMixer.Logic.ChampionStatsCalculatorExtensions, GpuGearMixer.Logic")
        NullLogger = System.Type.GetType(
            "Microsoft.Extensions.Logging.Abstractions.NullLogger, Microsoft.Extensions.Logging.Abstractions"
        )
        null_logger = NullLogger.GetProperty("Instance").GetValue(None, None)

        updated = JsonConvert.DeserializeObject[UpdatedRaidData](json.dumps(snapshot, ensure_ascii=False))
        blessings_response = requests.get(STATIC_BLESSINGS_URL, timeout=60)
        blessings_response.raise_for_status()
        static_data = JsonConvert.DeserializeObject[StaticDoubleAscendData](blessings_response.text)

        mapper = System.Activator.CreateInstance(System.Type.GetType("GpuGearMixer.Logic.RaidDataToRootMapper, GpuGearMixer.Logic"))
        root = System.Activator.CreateInstance(System.Type.GetType("GpuGearMixer.Logic.Models.Extracted.Root, GpuGearMixer.Logic"))
        root.StaticDoubleAscendData = static_data
        root = mapper.MapRaidDataToRoot(updated, root).Item1
        root.StaticDoubleAscendData = static_data
        root.HeroTypes = updated.HeroTypes

        hero_types = {hero_type.Id: hero_type for hero_type in updated.HeroTypes}
        fill_mastery = HeroExtensions.GetMethod("FillMasteryProperties")
        set_artifact_ids = HeroExtensions.GetMethod("SetArtifactIds")
        calc_base_stats = HeroExtensions.GetMethod("CalculateBaseStats")

        for hero in root.Heroes:
            hero_type = hero_types.get(hero.TypeId)
            if hero_type is None:
                continue
            hero.HeroType = hero_type
            fill_mastery.Invoke(None, System.Array[System.Object]([hero]))
            set_artifact_ids.Invoke(None, System.Array[System.Object]([hero, root, hero.Artifacts, True]))
            calc_base_stats.Invoke(None, System.Array[System.Object]([hero, root]))

        creator_type = System.Type.GetType("GpuGearMixer.Logic.ChampionArtifactsCreator, GpuGearMixer.Logic")
        build_type = System.Type.GetType("GpuGearMixer.Logic.Models.Own.Build, GpuGearMixer.Logic")
        null_rank_type = System.Type.GetType("GpuGearMixer.Logic.BuildRank.NullBuildRankEngine, GpuGearMixer.Logic")
        options_type = System.Type.GetType("GpuGearMixer.Logic.ChampionArtifactOptions, GpuGearMixer.Logic")
        weights_type = System.Type.GetType("GpuGearMixer.Logic.StatWeights, GpuGearMixer.Logic")
        prefs_type = System.Type.GetType("GpuGearMixer.Logic.GearFinderStatPreferences, GpuGearMixer.Logic")
        calc_type = System.Type.GetType("GpuGearMixer.Logic.ChampionStatsCalculator, GpuGearMixer.Logic")
        stat_kind_type = System.Type.GetType("HellHades.ArtifactExtractor.Models.StatKind, HellHades.ArtifactExtractor.Models")
        empty_stat_kinds = System.Array.CreateInstance(stat_kind_type, 0)
        set_artifacts_method = [
            method
            for method in CalcExtensions.GetMethods()
            if method.Name == "SetArtifacts" and "ChampionArtifact[]" in str(method)
        ][0]

        stats_by_hero_id = {}
        for hero in root.Heroes:
            if hero.HeroType is None:
                continue
            build = System.Activator.CreateInstance(build_type, System.Array[System.Object]([False]))
            creator = System.Activator.CreateInstance(
                creator_type,
                System.Array[System.Object](
                    [hero, build, System.Activator.CreateInstance(null_rank_type), System.Activator.CreateInstance(prefs_type), null_logger]
                ),
            )
            options = System.Activator.CreateInstance(options_type)
            options.IncludeLockedArtifacts = True
            options.LimitToArtifactIds = hero.Artifacts
            champion_artifacts = creator.GetChampionArtifactsToMatch(
                options,
                root.Artifacts,
                System.Activator.CreateInstance(weights_type),
                System.Activator.CreateInstance(prefs_type),
                empty_stat_kinds,
            ).Item1
            calculator = System.Activator.CreateInstance(calc_type, hero, root)
            set_artifacts_method.Invoke(None, System.Array[System.Object]([calculator, champion_artifacts]))
            stats = calculator.ChampionStats
            stats_by_hero_id[int(hero.Id)] = {
                "hp": int(stats.Health.Value),
                "atk": int(stats.Attack.Value),
                "def": int(stats.Defence.Value),
                "spd": int(stats.FloatingPointSpeed.DisplayValue),
                "cRate": int(stats.CriticalRate.Value),
                "cDmg": int(stats.CriticalDamage.Value),
                "acc": int(stats.Accuracy.Value),
                "res": int(stats.Resistance.Value),
                "relicCount": 0 if hero.Relics is None else int(hero.Relics.Count),
            }
        return stats_by_hero_id
    except Exception as exc:
        print(f"WARN: HH internal stats indisponiveis, usando fallback manual ({exc})")
        return {}


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


def rank_level_multiplier(rank, level):
    coeffs = RANK_MULTIPLIER_COEFFS.get(to_int(rank))
    if not coeffs:
        return 1.0
    safe_level = max(1, min(to_int(level), RANK_MAX_LEVEL.get(to_int(rank), to_int(level) or 1)))
    if safe_level == 1:
        return coeffs["min"]
    if safe_level >= RANK_MAX_LEVEL.get(to_int(rank), safe_level):
        return coeffs["max"]
    return (safe_level / coeffs["a"]) ** 2 + (safe_level / coeffs["b"]) + coeffs["c"]


def add_stat_bonus(bucket, kind, value, is_absolute):
    if not kind or not value:
        return
    stat = normalize_stat_kind(kind)
    if stat == "HP":
        target = "flat" if is_absolute else "pct"
        bucket["hp"][target] += value
    elif stat == "HP_PCT":
        bucket["hp"]["pct"] += value
    elif stat == "ATK":
        target = "flat" if is_absolute else "pct"
        bucket["atk"][target] += value
    elif stat == "ATK_PCT":
        bucket["atk"]["pct"] += value
    elif stat == "DEF":
        target = "flat" if is_absolute else "pct"
        bucket["def"][target] += value
    elif stat == "DEF_PCT":
        bucket["def"]["pct"] += value
    elif stat == "SPD":
        bucket["spd"] += value
    elif stat == "ACC":
        bucket["acc"] += value if is_absolute else value * 100
    elif stat == "RES":
        bucket["res"] += value if is_absolute else value * 100
    elif stat == "C_RATE":
        bucket["cRate"] += value if is_absolute else value * 100
    elif stat == "C_DMG":
        bucket["cDmg"] += value if is_absolute else value * 100


def add_snapshot_bonus(bucket, bonus):
    if not bonus:
        return
    kind_name = BONUS_KIND_ID_MAP.get(to_int(bonus.get("kind")))
    if not kind_name:
        return
    total_value = (
        parse_float(bonus.get("value"))
        + parse_float(bonus.get("enhancement"))
        + parse_float(bonus.get("rarityBasedPowerUpValue"))
    )
    add_stat_bonus(bucket, kind_name, total_value, parse_bool(bonus.get("isAbsolute")))


def apply_effects(bucket, effects):
    bucket["hp"]["pct"] += effects.get("hp_pct", 0.0)
    bucket["atk"]["pct"] += effects.get("atk_pct", 0.0)
    bucket["def"]["pct"] += effects.get("def_pct", 0.0)
    bucket["spdPct"] += effects.get("spd_pct", 0.0)
    bucket["acc"] += effects.get("acc", 0.0)
    bucket["res"] += effects.get("res", 0.0)
    bucket["cRate"] += effects.get("cRate", 0.0)
    bucket["cDmg"] += effects.get("cDmg", 0.0)


def add_set_bonus(bucket, set_counts):
    for set_id, count in set_counts.items():
        config = SET_BONUS_CONFIG.get(set_id)
        if not config:
            continue
        activations = count // config["pieces"]
        if activations <= 0:
            continue
        effects = config.get("effects") or {}
        for _ in range(activations):
            apply_effects(bucket, effects)

    for set_id, steps in VARIABLE_SET_STEPS.items():
        count = set_counts.get(set_id, 0)
        if not count:
            continue
        for threshold, effects in steps:
            if count >= threshold:
                apply_effects(bucket, effects)


def count_filled_guardian_slots(snapshot, hero_type):
    faction_key = FACTION_GUARDIAN_KEY.get(to_int(hero_type.get("fraction")))
    rarity_key = RARITY_GUARDIAN_KEY.get(to_int(hero_type.get("rarity")))
    if not faction_key or not rarity_key:
        return 0
    rows = (((snapshot.get("guardians") or {}).get(faction_key) or {}).get(rarity_key)) or []
    return sum(1 for row in rows if row.get("firstHero") or row.get("secondHero"))


def add_faction_guardian_bonus(bucket, snapshot, hero_type):
    filled = count_filled_guardian_slots(snapshot, hero_type)
    rarity = to_int(hero_type.get("rarity"))
    if filled <= 0 or rarity not in {3, 4, 5}:
        return

    acc_res_bonus = {5: 30, 4: 15, 3: 7}[rarity]
    spd_bonus = {5: 10, 4: 6, 3: 3}[rarity]

    if filled >= 1:
        bucket["hp"]["pct"] += 0.10
    if filled >= 2:
        bucket["atk"]["pct"] += 0.10
    if filled >= 3:
        bucket["acc"] += acc_res_bonus
        bucket["res"] += acc_res_bonus
    if filled >= 4:
        bucket["def"]["pct"] += 0.10
    if filled >= 5:
        bucket["spd"] += spd_bonus


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
    artifacts_by_id = {to_int(artifact.get("id")): artifact for artifact in snapshot.get("artifacts") or []}
    hh_stat_map = build_hh_internal_stat_map(snapshot)

    for champion in champions:
        hero = heroes_by_id.get(champion["heroId"]) or {}
        hero_type = hero_types.get(to_int(hero.get("typeId"))) or {}
        form = (hero_type.get("forms") or [{}])[0]
        base_stats = form.get("baseStats") or {}
        affinity_id = to_int(form.get("element"))
        role_id = to_int(form.get("role"))
        gh_affinity = GREAT_HALL_AFFINITY_MAP.get(affinity_id, "")
        gh_stats = great_hall.get(gh_affinity) or {}
        equipped_items = [
            artifacts_by_id.get(to_int(artifact_id))
            for artifact_id in (hero.get("artifacts") or [])
            if artifacts_by_id.get(to_int(artifact_id))
        ]
        set_counts = Counter(
            set_id
            for item in equipped_items
            for set_id in [to_int(item.get("set"))]
            if set_id > 0
        )
        stat_bucket = {
            "hp": {"flat": 0.0, "pct": 0.0},
            "atk": {"flat": 0.0, "pct": 0.0},
            "def": {"flat": 0.0, "pct": 0.0},
            "spd": 0.0,
            "spdPct": 0.0,
            "acc": 0.0,
            "res": 0.0,
            "cRate": 0.0,
            "cDmg": 0.0,
        }

        for item in equipped_items:
            add_snapshot_bonus(stat_bucket, item.get("primaryBonus"))
            for bonus in item.get("secondaryBonuses") or []:
                add_snapshot_bonus(stat_bucket, bonus)
            add_snapshot_bonus(stat_bucket, item.get("ascendBonus"))

        add_set_bonus(stat_bucket, set_counts)
        add_faction_guardian_bonus(stat_bucket, snapshot, hero_type)

        books_applied = sum(max(0, int(level) - 1) for level in (hero.get("skillLevels") or {}).values())
        multiplier = rank_level_multiplier(champion["grade"], champion["level"])
        hp_base = parse_float(base_stats.get("health")) * 15 * multiplier
        atk_base = parse_float(base_stats.get("attack")) * multiplier
        def_base = parse_float(base_stats.get("defence")) * multiplier
        spd_base = parse_float(base_stats.get("speed"))
        c_rate_base = parse_float(base_stats.get("criticalChance"))
        c_dmg_base = parse_float(base_stats.get("criticalDamage"))
        acc_base = parse_float(base_stats.get("accuracy"))
        res_base = parse_float(base_stats.get("resistance"))

        gh_hp_pct = parse_float(gh_stats.get("Health")) * 0.02
        gh_atk_pct = parse_float(gh_stats.get("Attack")) * 0.02
        gh_def_pct = parse_float(gh_stats.get("Defense")) * 0.02
        gh_c_dmg = parse_float(gh_stats.get("CriticalDamage")) * 2
        gh_acc = parse_float(gh_stats.get("Accuracy")) * 4
        gh_res = parse_float(gh_stats.get("Resistance")) * 4

        champion["role"] = ROLE_PT.get(role_id, "Indefinido")
        champion["affinity"] = AFFINITY_PT.get(affinity_id, "")
        champion["typeId"] = to_int(hero.get("typeId"))
        champion["shortName"] = clean_text(hero_type.get("shortName") or champion.get("shortName") or champion["name"])
        champion["booksApplied"] = books_applied
        champion["masteryTotal"] = len(hero.get("masteries") or [])
        champion["equippedItemCount"] = len(equipped_items)
        champion["relicCount"] = len(hero.get("relics") or [])
        champion["equippedSets"] = [
            {"setId": set_id, "name": set_name_pt(set_id), "count": count}
            for set_id, count in sorted(set_counts.items(), key=lambda entry: (-entry[1], entry[0]))
        ]
        hp_total = hp_base * (1 + stat_bucket["hp"]["pct"] + gh_hp_pct) + stat_bucket["hp"]["flat"]
        atk_total = atk_base * (1 + stat_bucket["atk"]["pct"] + gh_atk_pct) + stat_bucket["atk"]["flat"]
        def_total = def_base * (1 + stat_bucket["def"]["pct"] + gh_def_pct) + stat_bucket["def"]["flat"]
        spd_total = spd_base * (1 + stat_bucket["spdPct"]) + stat_bucket["spd"]
        c_rate_total = c_rate_base + stat_bucket["cRate"]
        c_dmg_total = c_dmg_base + stat_bucket["cDmg"] + gh_c_dmg
        acc_total = acc_base + stat_bucket["acc"] + gh_acc
        res_total = res_base + stat_bucket["res"] + gh_res

        champion["baseStats"] = {
            "hp": int(round(hp_base)),
            "atk": int(round(atk_base)),
            "def": int(round(def_base)),
            "spd": int(round(spd_base)),
            "cRate": int(round(c_rate_base)),
            "cDmg": int(round(c_dmg_base)),
            "acc": int(round(acc_base)),
            "res": int(round(res_base)),
        }
        champion["bonusStats"] = {
            "hp": int(round(hp_total - hp_base)),
            "atk": int(round(atk_total - atk_base)),
            "def": int(round(def_total - def_base)),
            "spd": int(round(spd_total - spd_base)),
            "cRate": int(round(c_rate_total - c_rate_base)),
            "cDmg": int(round(c_dmg_total - c_dmg_base)),
            "acc": int(round(acc_total - acc_base)),
            "res": int(round(res_total - res_base)),
        }
        champion["buildStats"] = {
            "hp": int(round(hp_total)),
            "atk": int(round(atk_total)),
            "def": int(round(def_total)),
            "spd": int(round(spd_total)),
            "cRate": int(round(c_rate_total)),
            "cDmg": int(round(c_dmg_total)),
            "acc": int(round(acc_total)),
            "res": int(round(res_total)),
        }
        hh_stats = hh_stat_map.get(champion["heroId"])
        if hh_stats:
            champion["buildStats"] = {
                "hp": int(hh_stats["hp"]),
                "atk": int(hh_stats["atk"]),
                "def": int(hh_stats["def"]),
                "spd": int(hh_stats["spd"]),
                "cRate": int(hh_stats["cRate"]),
                "cDmg": int(hh_stats["cDmg"]),
                "acc": int(hh_stats["acc"]),
                "res": int(hh_stats["res"]),
            }
            champion["bonusStats"] = {
                key: int(champion["buildStats"][key] - champion["baseStats"][key])
                for key in champion["baseStats"]
            }
            champion["relicCount"] = max(champion["relicCount"], int(hh_stats.get("relicCount", 0)))

        extra_speed = RELIC_SPEED_RECONCILIATION.get(champion["heroId"], 0)
        if extra_speed:
            champion["buildStats"]["spd"] += extra_speed
            champion["bonusStats"]["spd"] += extra_speed

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
                "setName": set_name_pt(set_id),
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
        "updatedOn": snapshot_updated_on(snapshot),
        "accountName": snapshot.get("name", ""),
        "userId": snapshot.get("userId", ""),
    }
    champions = build_champion_details(load_champions(snapshot), snapshot)
    items = load_items(snapshot)
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

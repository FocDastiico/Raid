import json
import re
import unicodedata
import urllib.request
from pathlib import Path


BASE = Path(".")
DATA_JS = BASE / "raid_simple_dashboard_data.js"
PROFILES_DIR = BASE / "champ_profiles"

FACTION_PATHS = {
    1: "BannerLords",
    2: "HighElves",
    3: "SacredOrder",
    4: "CovenOfMagi",
    5: "OgrynTribes",
    6: "LizardMen",
    7: "Skinwalkers",
    8: "Orcs",
    9: "Demonspawn",
    10: "UndeadHordes",
    11: "DarkElves",
    12: "KnightsRevenant",
    13: "Barbarians",
    14: "SylvanWatchers",
    15: "Shadowkin",
    16: "Dwarves",
    17: "Argonites",
}


def load_dashboard_data():
    text = DATA_JS.read_text(encoding="utf-8")
    prefix = "window.RAID_SIMPLE_DASHBOARD_DATA = "
    return json.loads(text[len(prefix):].rstrip(" ;\n"))


def slugify(value):
    value = "".join(
        ch for ch in unicodedata.normalize("NFD", str(value or ""))
        if unicodedata.category(ch) != "Mn"
    )
    value = re.sub(r"[^a-zA-Z0-9]+", "", value)
    return value.lower()


def hh_image_name(value):
    value = "".join(
        ch for ch in unicodedata.normalize("NFD", str(value or ""))
        if unicodedata.category(ch) != "Mn"
    )
    return re.sub(r"[^a-zA-Z0-9]+", "", value)


def candidate_urls(champion):
    faction = FACTION_PATHS.get(int(champion.get("factionId") or 0))
    rarity = champion.get("rarity")
    if not faction or not rarity:
      return []

    names = []
    for raw in (champion.get("name"), champion.get("shortName")):
        image_name = hh_image_name(raw)
        if image_name and image_name not in names:
            names.append(image_name)

    return [
        f"https://raidoptimiser.hellhades.com/assets/ChampionsIcons/{faction}/{rarity}/{name}.png"
        for name in names
    ]


def download_first_image(urls):
    for url in urls:
        request = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        try:
            with urllib.request.urlopen(request, timeout=10) as response:
                content_type = response.getheader("Content-Type") or ""
                if not content_type.startswith("image/"):
                    continue
                return response.read()
        except Exception:
            continue
    return None


def main():
    data = load_dashboard_data()
    PROFILES_DIR.mkdir(parents=True, exist_ok=True)

    downloaded = 0
    skipped = 0

    for champion in data.get("champions", []):
        target_names = []
        for raw in (champion.get("name"), champion.get("shortName")):
            slug = slugify(raw)
            if slug and slug not in target_names:
                target_names.append(slug)

        if not target_names:
            continue

        if any((PROFILES_DIR / f"{slug}_profile.png").exists() for slug in target_names):
            skipped += 1
            continue

        content = download_first_image(candidate_urls(champion))
        if not content:
            continue

        for slug in target_names:
            (PROFILES_DIR / f"{slug}_profile.png").write_bytes(content)
        downloaded += 1

    print(f"downloaded={downloaded}")
    print(f"skipped={skipped}")


if __name__ == "__main__":
    main()

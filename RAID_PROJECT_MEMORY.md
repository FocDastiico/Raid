# RAID Project Memory

Updated on: 2026-03-30

## Main project
- Primary project in this workspace: `raid_simple_hh_dashboard.html`
- Main generated data file: `raid_simple_dashboard_data.js`
- Main data builder: `generate_simple_dashboard_data.py`

## Product intent
- This dashboard is for Luiz's private use in RAID: Shadow Legends.
- The goal is practical decision support for bosses, champions and items.
- It can reuse HellHades APIs/assets/tools when useful, but the product itself is a custom personal dashboard, not a public clone.

## UX direction
- Keep the UI simpler than HellHades and optimized for fast reading.
- Favor clear champion/build information over dense tables.
- Show visual cues for equipped sets directly on champion cards.
- Keep the top header focused on the product title and account information.

## Confirmed decisions
- The main project to continue evolving is `raid_simple_hh_dashboard.html`.
- Header should keep only `RAID TEAM DASHBOARD` and account information.
- Navigation for `Bosses`, `Campeoes` and `Itens` should live beside the header content.
- Champion presentation should be more visual and easier to understand.
- Champion cards should show set imagery, and may use 2 columns on wide screens or 1 column when space is tighter.

## Notes for future edits
- Prefer preserving the existing dark RAID-inspired visual language.
- Keep HellHades integration as a source of data/assets, not as the UX goal.
- When improving champion cards, prioritize readability, build summary and equipped set visibility.

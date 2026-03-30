# RAID Team Dashboard

Dashboard privado para apoio no jogo RAID: Shadow Legends.

## Objetivo
- Organizar boss info, roster e sets de forma mais visual.
- Reaproveitar algumas ferramentas e assets do HellHades sem depender do mesmo UX.
- Facilitar colaboracao de desenvolvimento em um repositorio privado.

## Arquivos principais
- `raid_simple_hh_dashboard.html`: dashboard principal.
- `generate_simple_dashboard_data.py`: gera os dados consumidos pelo dashboard.
- `browser_extension/hh_live_viewer/`: extensao auxiliar para captura local.
- `RAID_PROJECT_MEMORY.md`: contexto e decisoes do projeto.

## Observacao importante
Arquivos sensiveis/privados e exports da conta foram excluidos do Git via `.gitignore`.

Se for necessario compartilhar dados com seguranca, o ideal e gerar uma versao sanitizada antes de subir.

## Push inicial para GitHub
Depois de criar um repositorio privado no GitHub:

```powershell
git remote add origin https://github.com/SEU_USUARIO/SEU_REPOSITORIO.git
git push -u origin main
```

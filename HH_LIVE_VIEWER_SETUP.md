# HH Live Viewer

Esta extensao do Opera GX captura o estado da pagina do HellHades e envia os dados para um servidor local no seu PC.

## O que ela salva

- URL atual
- titulo da pagina
- texto visivel principal da tela
- alguns botoes e titulos visiveis
- uma screenshot da aba

Os arquivos sao salvos em `hh_live_feed/`.

Agora o bridge tambem salva o `access_token` da sua sessao do HellHades em `hh_live_feed/latest_auth.json` para permitir consultas autenticadas aos endpoints oficiais de `TeamSuggestion`.

## 1. Iniciar o servidor local

No PowerShell, dentro desta pasta do projeto:

```powershell
python .\hh_live_bridge.py
```

Se estiver tudo certo, ele vai ficar ouvindo em:

```text
http://127.0.0.1:8765
```

## 2. Instalar a extensao no Opera GX

1. Abra `opera://extensions`
2. Ative `Developer mode`
3. Clique em `Load unpacked`
4. Selecione a pasta `browser_extension/hh_live_viewer`

## 3. Usar

1. Entre no site do HellHades
2. Navegue normalmente
3. A extensao envia snapshots automaticamente
4. Se quiser, clique no icone da extensao e use `Enviar agora`

## 3.1. Para liberar o Team Suggestion oficial

1. Esteja logado no `raidoptimiser.hellhades.com`
2. Abra qualquer pagina do optimizer
3. Espere a extensao capturar a tela ou clique em `Enviar agora`
4. O bridge vai salvar o token localmente

Depois disso, a pagina do projeto Raid pode consultar o backend oficial do HellHades pelo bridge local.

## 4. Onde eu vou ler os dados

Os ultimos dados ficam em:

- `hh_live_feed/latest_snapshot.json`
- imagens em `hh_live_feed/*.png`

## Observacoes

- A captura automatica tenta enviar so quando percebe mudanca na pagina
- O screenshot e da aba visivel naquele momento
- Se o servidor local nao estiver rodando, a extensao vai mostrar falha no status

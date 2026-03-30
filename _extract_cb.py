import ctypes
import ctypes.wintypes as wt
import json
import os
import re
import subprocess
from pathlib import Path

import requests

PROCESS_QUERY_LIMITED_INFORMATION = 0x1000

# Setup APIs
kernel32 = ctypes.WinDLL('kernel32', use_last_error=True)
psapi = ctypes.WinDLL('psapi', use_last_error=True)

OpenProcess = kernel32.OpenProcess
OpenProcess.argtypes = [wt.DWORD, wt.BOOL, wt.DWORD]
OpenProcess.restype = wt.HANDLE

CloseHandle = kernel32.CloseHandle
CloseHandle.argtypes = [wt.HANDLE]
CloseHandle.restype = wt.BOOL

EnumProcesses = psapi.EnumProcesses
EnumProcesses.argtypes = [ctypes.POINTER(wt.DWORD), wt.DWORD, ctypes.POINTER(wt.DWORD)]
EnumProcesses.restype = wt.BOOL

GetProcessImageFileNameW = psapi.GetProcessImageFileNameW
GetProcessImageFileNameW.argtypes = [wt.HANDLE, wt.LPWSTR, wt.DWORD]
GetProcessImageFileNameW.restype = wt.DWORD


def list_pids():
    arr = (wt.DWORD * 4096)()
    needed = wt.DWORD()
    if not EnumProcesses(arr, ctypes.sizeof(arr), ctypes.byref(needed)):
        raise OSError('EnumProcesses failed')
    count = needed.value // ctypes.sizeof(wt.DWORD)
    return [arr[i] for i in range(count)]


def get_image_name(pid):
    h = OpenProcess(PROCESS_QUERY_LIMITED_INFORMATION, False, pid)
    if not h:
        return None
    try:
        buf = ctypes.create_unicode_buffer(1024)
        n = GetProcessImageFileNameW(h, buf, len(buf))
        if n == 0:
            return None
        return os.path.basename(buf.value)
    finally:
        CloseHandle(h)


def find_extractor_pid():
    candidates = []
    for pid in list_pids():
        name = get_image_name(pid)
        if not name:
            continue
        low = name.lower()
        if ('hellhades.artifactextract' in low) or ('raidextractor' in low):
            candidates.append((pid, name))
    if not candidates:
        return None, []
    # prefer the exact executable if present
    for pid, name in candidates:
        if name.lower() == 'hellhades.artifactextractor.exe':
            return pid, candidates
    return candidates[0][0], candidates


def dump_process(pid, dump_path: Path):
    cmd = f'rundll32 C:\\Windows\\System32\\comsvcs.dll, MiniDump {pid} "{dump_path}" full'
    completed = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    return completed.returncode, completed.stdout, completed.stderr


def extract_jwt(dump_path: Path):
    data = dump_path.read_bytes()
    pat = re.compile(rb'eyJ[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}')
    matches = pat.findall(data)
    # choose longest plausible token
    toks = sorted({m.decode('ascii', errors='ignore') for m in matches}, key=len, reverse=True)
    return toks[0] if toks else None


def call_account_api(jwt):
    url = 'https://raidoptimiser.hellhades.com/api/Account'
    headers = {'Authorization': f'Bearer {jwt}'}
    r = requests.get(url, headers=headers, timeout=30)
    r.raise_for_status()
    return r.json()


def hero_name_maps(account):
    hero_types = account.get('heroTypes') or []
    heroes = account.get('heroes') or []

    type_name = {}
    for t in hero_types:
        tid = t.get('id')
        nm = t.get('name')
        if tid is not None and nm:
            type_name[tid] = nm

    hero_to_name = {}
    for h in heroes:
        hid = h.get('id')
        htid = h.get('heroTypeId')
        nm = type_name.get(htid)
        if hid is not None and nm:
            hero_to_name[hid] = nm
    return hero_to_name


def extract_presets(account):
    presets = account.get('battlePresets') or []
    if isinstance(presets, dict):
        presets = [presets]
    return presets


def normalize_champion_slots(preset):
    # try to discover champion ID slots from various possible field shapes
    out = []

    # 1) direct list fields
    for key in ['heroIds', 'championIds', 'heroes', 'champions', 'slots', 'team', 'lineup']:
        v = preset.get(key)
        if isinstance(v, list):
            vals = []
            for item in v:
                if isinstance(item, int):
                    vals.append(item)
                elif isinstance(item, dict):
                    for k in ['heroId', 'championId', 'id']:
                        if isinstance(item.get(k), int):
                            vals.append(item[k])
                            break
            if vals:
                out = vals
                break

    # 2) nested data object
    if not out and isinstance(preset.get('data'), dict):
        data = preset['data']
        for key in ['heroIds', 'championIds', 'heroes', 'champions', 'slots', 'team', 'lineup']:
            v = data.get(key)
            if isinstance(v, list):
                vals = []
                for item in v:
                    if isinstance(item, int):
                        vals.append(item)
                    elif isinstance(item, dict):
                        for k in ['heroId', 'championId', 'id']:
                            if isinstance(item.get(k), int):
                                vals.append(item[k])
                                break
                if vals:
                    out = vals
                    break

    return out[:5]


def pick_cb_candidates(presets):
    cands = []
    for p in presets:
        text = json.dumps(p, ensure_ascii=False).lower()
        score = 0
        for kw in ['clan boss', 'clanboss', 'demon lord', 'cb', 'brutal', 'nightmare', 'ultra nightmare', 'ultranightmare', 'nm', 'unm']:
            if kw in text:
                score += 1
        if score > 0:
            cands.append((score, p))
    cands.sort(key=lambda x: x[0], reverse=True)
    return [p for _, p in cands]


def main():
    cwd = Path.cwd()
    dump_path = cwd / 'hh_extractor_tmp.dmp'
    out_raw = cwd / 'HH_battle_presets_raw.json'
    out_cb = cwd / 'HH_cb_preset_candidates.json'

    pid, candidates = find_extractor_pid()
    if not pid:
        print('ERRO: Não encontrei processo do HellHades Extractor em execução.')
        print('Candidatos:', candidates)
        return 2

    rc, so, se = dump_process(pid, dump_path)
    if rc != 0 or (not dump_path.exists()):
        print('ERRO: Falha ao gerar dump do processo.')
        print('returncode:', rc)
        print('stdout:', so)
        print('stderr:', se)
        return 3

    jwt = None
    try:
        jwt = extract_jwt(dump_path)
    finally:
        try:
            dump_path.unlink(missing_ok=True)
        except Exception:
            pass

    if not jwt:
        print('ERRO: Não foi possível extrair JWT do dump.')
        return 4

    account = call_account_api(jwt)
    presets = extract_presets(account)
    hero_map = hero_name_maps(account)

    # Save raw presets
    out_raw.write_text(json.dumps(presets, ensure_ascii=False, indent=2), encoding='utf-8')

    cb_candidates = pick_cb_candidates(presets)
    enriched = []
    for p in cb_candidates:
        slots = normalize_champion_slots(p)
        names = [hero_map.get(hid, f'hero#{hid}') for hid in slots]
        enriched.append({
            'id': p.get('id'),
            'name': p.get('name') or p.get('title') or p.get('presetName'),
            'possibleChampionIds': slots,
            'possibleChampionNames': names,
            'raw': p,
        })

    out_cb.write_text(json.dumps(enriched, ensure_ascii=False, indent=2), encoding='utf-8')

    print(f'OK: presets={len(presets)} cb_candidates={len(enriched)}')
    for i, e in enumerate(enriched[:10], 1):
        nm = e['name'] or '(sem nome)'
        champs = ', '.join(e['possibleChampionNames']) if e['possibleChampionNames'] else 'sem slots detectados'
        print(f'{i}. {nm}: {champs}')

    return 0


if __name__ == '__main__':
    raise SystemExit(main())

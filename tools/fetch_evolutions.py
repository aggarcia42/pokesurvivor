#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Baja UNA vez las cadenas de evolución de PokeAPI y las deja en
js/data/evolutions.js. El juego no toca internet.

    python tools/fetch_evolutions.py

Reglas (ver docs/superpowers/specs/2026-10-11-in-run-evolution-design.md):
  level-up con min_level  -> ese nivel
  trade                   -> 50
  cualquier otra cosa     -> 36 (piedras, amistad, objetos, lugares...)
Los destinos que no están en el juego (formas regionales...) se descartan.
Las respuestas crudas se guardan en tools/cache/pokeapi/ para no volver a bajarlas.
"""
import io
import json
import os
import re
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor

API = 'https://pokeapi.co/api/v2'
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, 'js', 'data', 'evolutions.js')
CACHE = os.path.join(ROOT, 'tools', 'cache', 'pokeapi')
TRADE_LVL, OTHER_LVL = 50, 36


def game_dexes():
    src = io.open(os.path.join(ROOT, 'js', 'data', 'pokedex.js'), encoding='utf-8').read()
    return [int(m) for m in re.findall(r'^\s*\{"dex":(\d+),', src, re.M)]


def get(url, retries=3):
    os.makedirs(CACHE, exist_ok=True)
    key = re.sub(r'[^a-z0-9]+', '_', url.replace(API + '/', '').lower()).strip('_') + '.json'
    path = os.path.join(CACHE, key)
    if os.path.exists(path):
        return json.load(io.open(path, encoding='utf-8'))
    for _ in range(retries):
        try:
            req = urllib.request.Request(url, headers={'User-Agent': 'pokesurvivor/1.0'})
            with urllib.request.urlopen(req, timeout=40) as r:
                data = json.load(r)
            io.open(path, 'w', encoding='utf-8').write(json.dumps(data))
            return data
        except urllib.error.HTTPError as e:
            if e.code == 404:
                return None
        except Exception:
            pass
    return None


def level_for(details):
    """Nivel de evolución a partir de la lista evolution_details de PokeAPI."""
    if not details:
        return OTHER_LVL
    for d in details:                       # si alguna variante da nivel, ese
        if d.get('trigger', {}).get('name') == 'level-up' and d.get('min_level'):
            return int(d['min_level'])
    if any(d.get('trigger', {}).get('name') == 'trade' for d in details):
        return TRADE_LVL
    return OTHER_LVL


def species_id(url):
    return int(url.rstrip('/').split('/')[-1])


def main():
    dexes = game_dexes()
    in_game = set(dexes)
    print(f'{len(dexes)} especies del juego; bajando species para saber su cadena...')
    chain_urls = {}
    with ThreadPoolExecutor(max_workers=8) as ex:
        for dex, s in zip(dexes, ex.map(lambda d: get(f'{API}/pokemon-species/{d}'), dexes)):
            if s and s.get('evolution_chain'):
                chain_urls[dex] = s['evolution_chain']['url']
            else:
                print(f'  ! species {dex} sin cadena')
    urls = sorted(set(chain_urls.values()))
    print(f'{len(urls)} cadenas...')
    chains = {}
    with ThreadPoolExecutor(max_workers=8) as ex:
        for url, c in zip(urls, ex.map(get, urls)):
            if c:
                chains[url] = c['chain']
            else:
                print(f'  ! cadena {url} no disponible')

    evos = {}

    def walk(node, fam, parent_in_game):
        """Recorre la cadena. `fam` = primera especie del juego por encima (o None)."""
        me = species_id(node['species']['url'])
        here = me in in_game
        my_fam = fam if fam is not None else (me if here else None)
        if here:
            evos[me] = {'fam': my_fam, 'evo': []}
        for child in node.get('evolves_to', []):
            cid = species_id(child['species']['url'])
            if here and cid in in_game:
                evos[me]['evo'].append({'to': cid, 'lvl': level_for(child.get('evolution_details'))})
            elif not here and cid in in_game and parent_in_game is not None:
                # El padre no está en el juego (p. ej. un bebé sin sprite): el hijo cuelga del abuelo.
                evos[parent_in_game]['evo'].append({'to': cid, 'lvl': level_for(child.get('evolution_details'))})
            walk(child, my_fam, me if here else parent_in_game)

    for url, chain in chains.items():
        walk(chain, None, None)
    for d in dexes:                          # los que no salen en ninguna cadena: familia de uno
        evos.setdefault(d, {'fam': d, 'evo': []})

    lines = [
        '/* ============ evolutions.js — GENERADO, no editar a mano ============',
        ' * Lo produce tools/fetch_evolutions.py (cadenas de evolución de PokeAPI, bajadas una vez).',
        ' * dex -> { fam: especie base de la familia, evo: [{ to, lvl }] }',
        ' * Intercambio = nivel 50; piedras, amistad y demás = 36. Ayudas en js/data/evos.js.',
        ' */',
        'G.EVOS = {',
    ]
    for d in sorted(evos):
        lines.append(f'  {d}: ' + json.dumps(evos[d], separators=(',', ':')) + ',')
    lines += ['};', '']
    io.open(OUT, 'w', encoding='utf-8', newline='\n').write('\n'.join(lines))
    n_evo = sum(1 for e in evos.values() if e['evo'])
    print(f'{len(evos)} especies, {n_evo} con evolución -> js/data/evolutions.js')


if __name__ == '__main__':
    main()

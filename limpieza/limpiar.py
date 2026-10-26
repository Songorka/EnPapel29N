#!/usr/bin/env python3
"""Limpieza del ataque del 25-10-2026: contenido malicioso (falsa pantalla de Cloudflare con enlace a
varors.com) inyectado en entradas y páginas de Enpapel.

Uso (lo ejecuta .github/workflows/limpieza.yml al subir limpieza/orden.json):
  {"modo": "revisar"}   solo lee: qué está infectado, qué versión limpia hay, usuarios y accesos
  {"modo": "limpiar"}   devuelve cada entrada/página infectada a su última revisión limpia
Resultado en limpieza/resultado-<modo>.json (sin datos secretos).
"""
import base64, json, os, re, sys, time, urllib.error, urllib.parse, urllib.request

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
WP = os.environ.get('WP_URL', 'https://enpapel.es').rstrip('/')
USER = os.environ.get('WP_USER', '')
PWD = re.sub(r'\s+', '', os.environ.get('WP_APP_PASSWORD', ''))
MARCAS = ('varors.', 'site-verification-ok', 'Click to verify', 'Verify you are human')
DESDE = '2026-10-24T00:00:00'  # se puede cambiar con "desde" en orden.json


def api(metodo, ruta, datos=None):
    url = WP + '/wp-json/wp/v2/' + ruta.lstrip('/')
    h = {'Authorization': 'Basic ' + base64.b64encode(f'{USER}:{PWD}'.encode()).decode(),
         'User-Agent': 'EnPapel29N-limpieza/1.0', 'Accept': 'application/json'}
    cuerpo = None
    if datos is not None:
        cuerpo = json.dumps(datos).encode(); h['Content-Type'] = 'application/json'
    for i in range(3):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, cuerpo, h, method=metodo), timeout=120) as r:
                return json.loads(r.read().decode() or 'null'), r.headers
        except urllib.error.HTTPError as e:
            if e.code >= 500 and i < 2:
                time.sleep(5); continue
            return {'error': e.code, 'detalle': e.read().decode(errors='replace')[:300]}, {}
        except urllib.error.URLError:
            if i < 2:
                time.sleep(5); continue
            raise


def infectado(texto):
    return any(m in (texto or '') for m in MARCAS)


def campos(o):
    return {k: (o.get(k) or {}).get('raw', '') if isinstance(o.get(k), dict) else (o.get(k) or '')
            for k in ('title', 'content', 'excerpt')}


def todos(tipo):
    salida, pagina = [], 1
    while True:
        q = urllib.parse.urlencode({'per_page': 100, 'page': pagina, 'context': 'edit', 'status': 'any',
                                    'modified_after': DESDE, '_fields': 'id,link,status,modified,title,content,excerpt'})
        d, _ = api('GET', f'{tipo}?{q}')
        if not isinstance(d, list) or not d:
            break
        salida += d
        pagina += 1
    return salida


def version_limpia(tipo, pid):
    revs, _ = api('GET', f'{tipo}/{pid}/revisions?per_page=100&context=edit')
    if not isinstance(revs, list):
        return None, f'no se pueden leer las revisiones: {revs}'
    for r in sorted(revs, key=lambda r: r['date'], reverse=True):
        c = campos(r)
        if not any(infectado(v) for v in c.values()):
            return r, None
    return None, f'{len(revs)} revisiones, ninguna limpia'


def accesos():
    d, _ = api('GET', 'users?context=edit&per_page=100&_fields=id,username,name,email,roles,registered_date')
    usuarios = []
    for u in d if isinstance(d, list) else []:
        aps, _ = api('GET', f'users/{u["id"]}/application-passwords')
        usuarios.append({'id': u['id'], 'usuario': u.get('username'), 'nombre': u.get('name'),
                         'roles': u.get('roles'), 'alta': u.get('registered_date'),
                         'contrasenas_aplicacion': [{'nombre': a.get('name'), 'creada': a.get('created'),
                                                     'ultimo_uso': a.get('last_used'), 'ultima_ip': a.get('last_ip')}
                                                    for a in (aps if isinstance(aps, list) else [])]})
    plugins, _ = api('GET', 'plugins?_fields=plugin,name,version,status')
    return usuarios, plugins if isinstance(plugins, list) else plugins


def main():
    orden = json.load(open(os.path.join(RAIZ, 'limpieza', 'orden.json'), encoding='utf-8'))
    modo = orden.get('modo', 'revisar')
    global DESDE
    DESDE = orden.get('desde', DESDE)
    if modo == 'yo':   # comprobar con qué usuario y permisos entra la conexión del 29N
        r, h = api('GET', 'users/me?context=edit&_fields=id,username,roles,capabilities')
        caps = r.get('capabilities', {}) if isinstance(r, dict) else {}
        res = {'modo': modo, 'hora': time.strftime('%Y-%m-%d %H:%M UTC', time.gmtime()),
               'usuario': r.get('username') if isinstance(r, dict) else None,
               'roles': r.get('roles') if isinstance(r, dict) else None,
               'puede_crear_etiquetas': caps.get('manage_categories'), 'puede_publicar': caps.get('publish_posts'),
               'error': r.get('error') if isinstance(r, dict) else str(r),
               'detalle': r.get('detalle') if isinstance(r, dict) else None}
        json.dump(res, open(os.path.join(RAIZ, 'limpieza', 'resultado-yo.json'), 'w', encoding='utf-8'),
                  ensure_ascii=False, indent=1)
        return
    if modo == 'instalar':   # instalar y activar un plugin del directorio oficial de WordPress
        res = {'modo': modo, 'hora': time.strftime('%Y-%m-%d %H:%M UTC', time.gmtime())}
        r, _ = api('POST', 'plugins', {'slug': orden['slug'], 'status': 'active'})
        res['resultado'] = {k: r.get(k) for k in ('plugin', 'name', 'version', 'status', 'error', 'detalle')} \
            if isinstance(r, dict) else str(r)
        json.dump(res, open(os.path.join(RAIZ, 'limpieza', 'resultado-instalar.json'), 'w', encoding='utf-8'),
                  ensure_ascii=False, indent=1)
        return
    if modo == 'plugins':   # desactivar plugins por su nombre (no se borran)
        res = {'modo': modo, 'hora': time.strftime('%Y-%m-%d %H:%M UTC', time.gmtime()), 'cambios': []}
        lista, _ = api('GET', 'plugins?_fields=plugin,name,version,status')
        for nombre in orden['desactivar']:
            p = next((x for x in lista if x['name'].strip().lower() == nombre.strip().lower()), None)
            if not p:
                res['cambios'].append({'nombre': nombre, 'error': 'no encontrado'}); continue
            r, _ = api('POST', 'plugins/' + p['plugin'].removesuffix('.php'), {'status': 'inactive'})
            res['cambios'].append({'nombre': nombre, 'estado': r.get('status') if isinstance(r, dict) else None,
                                   'error': r.get('error') if isinstance(r, dict) else str(r)})
        final, _ = api('GET', 'plugins?_fields=name,version,status')
        res['plugins'] = final
        json.dump(res, open(os.path.join(RAIZ, 'limpieza', 'resultado-plugins.json'), 'w', encoding='utf-8'),
                  ensure_ascii=False, indent=1)
        return
    if modo == 'autores':   # quién hizo cada cambio (revisiones) en las entradas atacadas
        res = {'modo': modo, 'hora': time.strftime('%Y-%m-%d %H:%M UTC', time.gmtime()), 'entradas': []}
        for tipo, pid in orden['ids']:
            revs, _ = api('GET', f'{tipo}/{pid}/revisions?per_page=20&context=edit&_fields=id,author,date,date_gmt,content')
            res['entradas'].append({'id': pid, 'revisiones': [
                {'rev': r['id'], 'autor': r['author'], 'fecha_utc': r['date_gmt'],
                 'infectada': infectado((r.get('content') or {}).get('raw', ''))} for r in revs]
                if isinstance(revs, list) else str(revs)})
        json.dump(res, open(os.path.join(RAIZ, 'limpieza', 'resultado-autores.json'), 'w', encoding='utf-8'),
                  ensure_ascii=False, indent=1)
        return
    if modo == 'perfiles':   # quitar permisos de edición a usuarios que ya no colaboran (su firma se mantiene)
        intocables = {1, 4, 6, 10} - set(orden.get('permitir', []))
        res = {'modo': modo, 'hora': time.strftime('%Y-%m-%d %H:%M UTC', time.gmtime()), 'usuarios': []}
        for uid in orden['ids']:
            if uid in intocables:
                res['usuarios'].append({'id': uid, 'omitido': 'protegido'}); continue
            u, _ = api('POST', f'users/{uid}', {'roles': [orden.get('rol', 'subscriber')]})
            res['usuarios'].append({'id': uid, 'nombre': u.get('name') if isinstance(u, dict) else None,
                                    'roles': u.get('roles') if isinstance(u, dict) else None,
                                    'error': u.get('error') if isinstance(u, dict) else str(u)})
        d, _ = api('GET', 'users?context=edit&per_page=100&_fields=id,name,roles')
        res['estado_final'] = d
        json.dump(res, open(os.path.join(RAIZ, 'limpieza', 'resultado-perfiles.json'), 'w', encoding='utf-8'),
                  ensure_ascii=False, indent=1)
        print(json.dumps(res, ensure_ascii=False)[:2000])
        return
    res = {'modo': modo, 'hora': time.strftime('%Y-%m-%d %H:%M UTC', time.gmtime()), 'elementos': []}
    for tipo in ('posts', 'pages'):
        for o in todos(tipo):
            c = campos(o)
            malos = [k for k, v in c.items() if infectado(v)]
            if not malos:
                continue
            r, problema = version_limpia(tipo, o['id'])
            e = {'tipo': tipo, 'id': o['id'], 'enlace': o.get('link'), 'modificado': o.get('modified'),
                 'campos_infectados': malos,
                 'version_limpia': r and {'id': r['id'], 'fecha': r['date']}, 'problema': problema}
            if modo == 'limpiar' and r:
                rc = campos(r)
                datos = {k: rc[k] for k in malos}
                p, _ = api('POST', f'{tipo}/{o["id"]}', datos)
                comprobado = isinstance(p, dict) and not any(infectado(v) for v in campos(p).values())
                e['limpiado'] = comprobado
                if not comprobado:
                    e['error'] = str(p)[:300]
            res['elementos'].append(e)
    res['total_infectados'] = len(res['elementos'])
    res['sin_version_limpia'] = sum(1 for e in res['elementos'] if not e['version_limpia'])
    if modo == 'limpiar':
        res['limpiados'] = sum(1 for e in res['elementos'] if e.get('limpiado'))
    else:
        res['usuarios'], res['plugins'] = accesos()
    json.dump(res, open(os.path.join(RAIZ, 'limpieza', f'resultado-{modo}.json'), 'w', encoding='utf-8'),
              ensure_ascii=False, indent=1)
    print(json.dumps({k: v for k, v in res.items() if k not in ('elementos', 'usuarios', 'plugins')}))


if __name__ == '__main__':
    main()

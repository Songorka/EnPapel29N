#!/usr/bin/env python3
"""Publica un post en X (con imagen) usando la API oficial y OAuth 1.0a (contexto de usuario).

Secretos de GitHub necesarios: X_API_KEY, X_API_SECRET, X_ACCESS_TOKEN, X_ACCESS_SECRET.
Uso desde publicar.py:  publicar_en_x(texto, ruta_imagen, alt) -> {'id': ..., 'enlace': ...}
Uso suelto (prueba):    python3 noticias/x_publicar.py "texto" ruta.png "texto alternativo"
"""
import base64, hashlib, hmac, json, os, secrets, sys, time, urllib.error, urllib.parse, urllib.request

CK = os.environ.get('X_API_KEY', '').strip()
CS = os.environ.get('X_API_SECRET', '').strip()
AT = os.environ.get('X_ACCESS_TOKEN', '').strip()
AS = os.environ.get('X_ACCESS_SECRET', '').strip()
UA = 'EnPapel29N/1.0'


def configurado():
    return all((CK, CS, AT, AS))


def _q(s):
    return urllib.parse.quote(str(s), safe='~-._')


def _firma(metodo, url, params_firma):
    o = {'oauth_consumer_key': CK, 'oauth_nonce': secrets.token_hex(16), 'oauth_signature_method': 'HMAC-SHA1',
         'oauth_timestamp': str(int(time.time())), 'oauth_token': AT, 'oauth_version': '1.0'}
    todos = dict(params_firma); todos.update(o)
    base = '&'.join([metodo.upper(), _q(url), _q('&'.join(f'{_q(k)}={_q(v)}' for k, v in sorted(todos.items())))])
    clave = f'{_q(CS)}&{_q(AS)}'
    o['oauth_signature'] = base64.b64encode(hmac.new(clave.encode(), base.encode(), hashlib.sha1).digest()).decode()
    return 'OAuth ' + ', '.join(f'{_q(k)}="{_q(v)}"' for k, v in sorted(o.items()))


def _peticion(metodo, url, cuerpo=None, tipo=None, params_firma=None):
    h = {'Authorization': _firma(metodo, url, params_firma or {}), 'User-Agent': UA}
    if tipo:
        h['Content-Type'] = tipo
    try:
        with urllib.request.urlopen(urllib.request.Request(url, cuerpo, h, method=metodo), timeout=90) as r:
            return json.loads(r.read().decode() or 'null')
    except urllib.error.HTTPError as e:
        raise RuntimeError(f'X respondió {e.code} en {url}: {e.read().decode(errors="replace")[:400]}')


def _multipart(campos, archivo_campo, nombre, datos, mime):
    limite = '----enpapel' + secrets.token_hex(8)
    partes = []
    for k, v in campos.items():
        partes.append(f'--{limite}\r\nContent-Disposition: form-data; name="{k}"\r\n\r\n{v}\r\n'.encode())
    partes.append(f'--{limite}\r\nContent-Disposition: form-data; name="{archivo_campo}"; filename="{nombre}"\r\n'
                  f'Content-Type: {mime}\r\n\r\n'.encode() + datos + b'\r\n')
    partes.append(f'--{limite}--\r\n'.encode())
    return b''.join(partes), f'multipart/form-data; boundary={limite}'


def subir_imagen(ruta, alt=''):
    datos = open(ruta, 'rb').read()
    errores = []
    # API v2 (actual)
    try:
        cuerpo, tipo = _multipart({'media_category': 'tweet_image', 'media_type': 'image/png'}, 'media',
                                  os.path.basename(ruta), datos, 'image/png')
        r = _peticion('POST', 'https://api.x.com/2/media/upload', cuerpo, tipo)
        mid = (r.get('data') or {}).get('id') or r.get('media_id_string')
        if mid:
            if alt:
                try:
                    _peticion('POST', 'https://api.x.com/2/media/metadata',
                              json.dumps({'id': mid, 'metadata': {'alt_text': {'text': alt[:1000]}}}).encode(), 'application/json')
                except RuntimeError:
                    pass
            return mid
        errores.append('v2 sin id: ' + json.dumps(r)[:200])
    except RuntimeError as e:
        errores.append(str(e))
    # API v1.1 (por si la v2 no está disponible)
    try:
        cuerpo, tipo = _multipart({}, 'media', os.path.basename(ruta), datos, 'image/png')
        r = _peticion('POST', 'https://upload.twitter.com/1.1/media/upload.json', cuerpo, tipo)
        return r['media_id_string']
    except (RuntimeError, KeyError) as e:
        errores.append(str(e))
    raise RuntimeError('No se pudo subir la imagen a X: ' + ' | '.join(errores))


def publicar_en_x(texto, ruta_imagen=None, alt=''):
    if not configurado():
        raise RuntimeError('Faltan los secretos de X en GitHub.')
    datos = {'text': texto}
    if ruta_imagen and os.path.exists(ruta_imagen):
        try:
            datos['media'] = {'media_ids': [subir_imagen(ruta_imagen, alt)]}
        except RuntimeError as e:
            print('Aviso: se publica sin imagen.', e, file=sys.stderr)
    r = _peticion('POST', 'https://api.x.com/2/tweets', json.dumps(datos).encode(), 'application/json')
    tid = r['data']['id']
    return {'id': tid, 'enlace': f'https://x.com/i/status/{tid}', 'con_imagen': 'media' in datos}


def texto_post(base, enlace, etiquetas=('#29N', '#Encuestas')):
    """Une el texto, el enlace y los hashtags sin pasar de 280 (un enlace cuenta 23)."""
    cola = ' '.join(e for e in etiquetas if e.lower() not in base.lower())
    def largo(t):
        return len(t) + 23 + 2 + (len(cola) + 1 if cola else 0)
    t = base.strip()
    while largo(t) > 280:
        t = t[:-2].rstrip() + '…'
    return f'{t}\n\n{enlace}' + (f' {cola}' if cola else '')


if __name__ == '__main__':
    print(json.dumps(publicar_en_x(sys.argv[1], sys.argv[2] if len(sys.argv) > 2 else None,
                                   sys.argv[3] if len(sys.argv) > 3 else ''), ensure_ascii=False))

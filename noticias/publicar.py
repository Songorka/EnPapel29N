#!/usr/bin/env python3
"""Publica en Enpapel (WordPress) las noticias que hay en noticias/cola/*.json.

Lo ejecuta GitHub Actions (.github/workflows/publicar-noticia.yml) con estos secretos:
  WP_USER          usuario de WordPress que creó la contraseña de aplicación
  WP_APP_PASSWORD  contraseña de aplicación de WordPress (no la contraseña normal)

Formato de cada fichero de la cola (JSON):
{
  "fecha": "2026-10-11",
  "estado": "publish" | "draft",
  "titulo": "...", "slug": "encuesta-...-29n", "extracto": "...",
  "contenido": "<!-- wp:heading --> ... (HTML en bloques de WordPress)",
  "categorias": [7041, 58], "autor": 4,
  "etiquetas": ["elecciones", "29N", "40dB", ...],
  "imagen": "noticias/imagenes/2026-10-11.png", "imagen_nombre": "encuesta-...png", "imagen_alt": "...",
  "seo": {"frase_clave": "...", "titulo": "...", "descripcion": "...",
          "social_titulo": "...", "social_descripcion": "...", "categoria_principal": 7041}
}
Resultado: noticias/publicadas/<fecha>.json con el enlace, y el fichero sale de la cola.
"""
import base64, glob, json, os, re, sys, time, urllib.error, urllib.parse, urllib.request

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
WP = os.environ.get('WP_URL', 'https://enpapel.es').rstrip('/')
USER = os.environ.get('WP_USER', '')
PWD = re.sub(r'\s+', '', os.environ.get('WP_APP_PASSWORD', '')).strip('"\'')
UA = 'Mozilla/5.0 (compatible; EnPapel29N-publicador/1.0; +https://songorka.github.io/EnPapel29N/)'


def api(metodo, ruta, datos=None, crudo=None, cabeceras=None, intentos=3):
    url = WP + '/wp-json/wp/v2/' + ruta.lstrip('/')
    h = {'Authorization': 'Basic ' + base64.b64encode(f'{USER}:{PWD}'.encode()).decode(),
         'User-Agent': UA, 'Accept': 'application/json'}
    cuerpo = None
    if datos is not None:
        cuerpo = json.dumps(datos).encode(); h['Content-Type'] = 'application/json'
    if crudo is not None:
        cuerpo = crudo
    h.update(cabeceras or {})
    for i in range(intentos):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, cuerpo, h, method=metodo), timeout=60) as r:
                return json.loads(r.read().decode() or 'null')
        except urllib.error.HTTPError as e:
            txt = e.read().decode(errors='replace')[:500]
            if e.code >= 500 and i < intentos - 1:
                time.sleep(5 * (i + 1)); continue
            pista = ''
            if e.code == 401:
                pista = (f' | Pista: la contraseña recibida tiene {len(PWD)} caracteres (deben ser 24, solo letras y números)'
                         f'{" y contiene caracteres raros" if not PWD.isalnum() else ""}.')
            raise SystemExit(f'ERROR {e.code} en {metodo} {ruta}: {txt}{pista}')
        except urllib.error.URLError as e:
            if i < intentos - 1:
                time.sleep(5 * (i + 1)); continue
            raise SystemExit(f'ERROR de conexión en {metodo} {ruta}: {e}')


def etiqueta_id(nombre):
    r = api('GET', 'tags?per_page=100&search=' + urllib.parse.quote(nombre))
    for t in r:
        if t['name'].strip().lower() == nombre.strip().lower():
            return t['id']
    return api('POST', 'tags', {'name': nombre})['id']


def subir_imagen(n):
    ruta = os.path.join(RAIZ, n['imagen'])
    nombre = n.get('imagen_nombre') or os.path.basename(ruta)
    with open(ruta, 'rb') as f:
        m = api('POST', 'media', crudo=f.read(), cabeceras={
            'Content-Type': 'image/png', 'Content-Disposition': f'attachment; filename="{nombre}"'})
    api('POST', f'media/{m["id"]}', {'alt_text': n.get('imagen_alt', ''), 'title': n['titulo']})
    return m['id']


def meta_seo(n):
    s = n.get('seo') or {}
    m = {
        '_yoast_wpseo_focuskw': s.get('frase_clave', ''),
        '_yoast_wpseo_title': (s['titulo'] + ' %%sep%% %%sitename%%') if s.get('titulo') else '',
        '_yoast_wpseo_metadesc': s.get('descripcion', ''),
        '_yoast_wpseo_opengraph-title': s.get('social_titulo', ''),
        '_yoast_wpseo_opengraph-description': s.get('social_descripcion', ''),
        '_yoast_wpseo_twitter-title': s.get('social_titulo', ''),
        '_yoast_wpseo_twitter-description': s.get('social_descripcion', ''),
        '_yoast_wpseo_schema_article_type': 'NewsArticle',
        '_yoast_wpseo_primary_category': str(s.get('categoria_principal', n['categorias'][0])),
    }
    return {k: v for k, v in m.items() if v}


def a_x(texto_base, enlace, imagen_rel, alt):
    """Publica en X si están los secretos. Nunca hace fallar la publicación en WordPress."""
    sys.path.insert(0, os.path.join(RAIZ, 'noticias'))
    import x_publicar as X
    if not X.configurado():
        return {'x': 'sin configurar'}
    try:
        texto = X.texto_post(texto_base, enlace)
        r = X.publicar_en_x(texto, os.path.join(RAIZ, imagen_rel) if imagen_rel else None, alt)
        return {'x_enlace': r['enlace'], 'x_con_imagen': r['con_imagen']}
    except Exception as e:
        return {'x_error': str(e)[:500]}


def publicar(ruta):
    n = json.load(open(ruta, encoding='utf-8'))
    fecha = n['fecha']; estado = n.get('estado', 'publish')
    if n.get('solo_x'):  # publicar en X una noticia que ya está en Enpapel
        res = dict(fecha=fecha, enlace=n['enlace'], **a_x(n['x_texto'], n['enlace'], n.get('imagen'), n.get('imagen_alt', '')))
        json.dump(res, open(os.path.join(RAIZ, 'noticias', 'publicadas', f'{fecha}-x.json'), 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
        os.remove(ruta); print(json.dumps(res, ensure_ascii=False)); return
    salida = os.path.join(RAIZ, 'noticias', 'publicadas', f'{fecha}.json')
    if n.get('corregir_id'):  # corregir el titular (u otros campos) de una noticia ya publicada; no toca X
        cambios = {k_wp: n[k] for k, k_wp in (('titulo', 'title'), ('extracto', 'excerpt')) if n.get(k)}
        p = api('POST', f'posts/{n["corregir_id"]}', cambios)
        if os.path.exists(salida):
            res = json.load(open(salida, encoding='utf-8'))
            if res.get('id') == p['id'] and n.get('titulo'):
                res['titulo'] = n['titulo']; res['corregido'] = True
                json.dump(res, open(salida, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
        os.remove(ruta); print('Corregida', p['id'], p['link']); return
    if estado == 'publish' and os.path.exists(salida) and json.load(open(salida)).get('estado') == 'publish':
        print(f'{fecha}: ya hay una noticia publicada hoy; no se publica otra.')
        os.remove(ruta); return
    for campo in ('titulo', 'contenido', 'categorias', 'imagen'):
        if not n.get(campo):
            raise SystemExit(f'{ruta}: falta el campo {campo}')
    tags = [etiqueta_id(t) for t in n.get('etiquetas', [])]
    media = subir_imagen(n)
    datos = {'title': n['titulo'], 'content': n['contenido'], 'excerpt': n.get('extracto', ''),
             'status': estado, 'categories': n['categorias'], 'tags': tags, 'featured_media': media,
             'author': n.get('autor', 4), 'comment_status': 'open'}
    if n.get('slug'):
        datos['slug'] = n['slug']
    meta = meta_seo(n)
    p = api('POST', 'posts', dict(datos, meta=meta) if meta else datos)
    # segunda pasada: Yoast recalcula con los campos SEO ya guardados
    p = api('POST', f'posts/{p["id"]}', {'meta': meta} if meta else {'excerpt': n.get('extracto', '')})
    res = {'fecha': fecha, 'estado': p['status'], 'id': p['id'], 'enlace': p['link'], 'titulo': n['titulo'],
           'imagen_id': media, 'seo_aplicado': bool(p.get('meta', {}).get('_yoast_wpseo_metadesc'))}
    if estado == 'publish' and p['status'] == 'publish' and n.get('x_texto'):
        res.update(a_x(n['x_texto'], p['link'], n['imagen'], n.get('imagen_alt', '')))
    os.makedirs(os.path.dirname(salida), exist_ok=True)
    if estado == 'draft':
        salida = salida.replace('.json', '-borrador.json')
    json.dump(res, open(salida, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    os.remove(ruta)
    print(json.dumps(res, ensure_ascii=False))


def main():
    if not USER or not PWD:
        raise SystemExit('Faltan los secretos WP_USER y WP_APP_PASSWORD en GitHub.')
    cola = sorted(glob.glob(os.path.join(RAIZ, 'noticias', 'cola', '*.json')))
    if not cola:
        print('No hay noticias en la cola.'); return
    for ruta in cola:
        publicar(ruta)


if __name__ == '__main__':
    try:
        main()
    except SystemExit as e:
        if e.code not in (None, 0):
            # deja el motivo en el repositorio (sin datos secretos) para poder revisarlo
            os.makedirs(os.path.join(RAIZ, 'noticias', 'publicadas'), exist_ok=True)
            with open(os.path.join(RAIZ, 'noticias', 'publicadas', 'ultimo-error.txt'), 'w', encoding='utf-8') as f:
                f.write(time.strftime('%Y-%m-%d %H:%M UTC', time.gmtime()) + '\n' + str(e.code) + '\n')
        raise

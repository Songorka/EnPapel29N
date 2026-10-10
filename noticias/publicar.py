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
import base64, glob, json, os, sys, time, urllib.error, urllib.parse, urllib.request

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
WP = os.environ.get('WP_URL', 'https://enpapel.es').rstrip('/')
USER = os.environ.get('WP_USER', '')
PWD = os.environ.get('WP_APP_PASSWORD', '').replace(' ', '')
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
            raise SystemExit(f'ERROR {e.code} en {metodo} {ruta}: {txt}')
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


def publicar(ruta):
    n = json.load(open(ruta, encoding='utf-8'))
    fecha = n['fecha']; estado = n.get('estado', 'publish')
    salida = os.path.join(RAIZ, 'noticias', 'publicadas', f'{fecha}.json')
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

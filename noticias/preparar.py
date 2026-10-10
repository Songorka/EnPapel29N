#!/usr/bin/env python3
"""Convierte el borrador de la noticia del día en un fichero listo para publicar.

Uso:  python3 noticias/preparar.py BORRADOR.json [--fecha AAAA-MM-DD] [--borrador]

BORRADOR.json (lo escribe la tarea diaria siguiendo noticias/plantilla.md):
{
  "titulo": "...", "slug": "encuesta-40db-...-29n", "extracto": "...",
  "frase_clave": "encuesta 40dB", "seo_titulo": "...", "seo_descripcion": "...",
  "social_titulo": "...", "social_descripcion": "...",
  "etiquetas": ["elecciones", "elecciones generales", "encuestas electorales", "29N", "40dB", "PP", "PSOE", "Vox"],
  "encuestadora": "40dB",
  "secciones": [ {"subtitulo": "Qué dice la encuesta de 40dB", "parrafos": ["...", "<em>...</em>"]}, ... ],
  "fichas": ["<strong>Ficha técnica:</strong> 40dB para ... <a href=\\"URL\\">Fuente</a>."]
}
Genera la imagen (noticias/imagen.py), monta el HTML en bloques y deja noticias/cola/<fecha>.json.
Al hacer push, GitHub Actions la publica y deja el enlace en noticias/publicadas/<fecha>.json.
"""
import argparse, json, os, re, subprocess, sys
from datetime import date

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MESES = ['enero', 'febrero', 'marzo', 'abril', 'mayo', 'junio', 'julio', 'agosto', 'septiembre', 'octubre', 'noviembre', 'diciembre']
CIERRE = '<em>Todas las encuestas, la media y el pactómetro, en <a href="https://enpapel.es/encuestas-29n/">enpapel.es/encuestas-29n</a>.</em>'


def bloque_p(t):
    return f'<!-- wp:paragraph -->\n<p>{t}</p>\n<!-- /wp:paragraph -->'


def bloque_h2(t):
    return f'<!-- wp:heading -->\n<h2 class="wp-block-heading">{t}</h2>\n<!-- /wp:heading -->'


def slugify(s):
    s = s.lower()
    for a, b in zip('áéíóúüñ', 'aeiouun'):
        s = s.replace(a, b)
    return re.sub(r'[^a-z0-9]+', '-', s).strip('-')


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('borrador')
    ap.add_argument('--fecha')
    ap.add_argument('--borrador', dest='es_borrador', action='store_true', help='publicar como borrador (prueba)')
    a = ap.parse_args()
    hoy = date.fromisoformat(a.fecha) if a.fecha else date.today()
    b = json.load(open(a.borrador, encoding='utf-8'))

    datos = open(os.path.join(RAIZ, 'index.html'), encoding='utf-8').read()
    D = json.loads(re.search(r'<script type="application/json" id="datos">(.*?)</script>', datos, re.S).group(1))
    if date.fromisoformat(D['vedaStart']) <= hoy < date.fromisoformat(D['vedaEnd']) and not a.es_borrador:
        sys.exit('Periodo de veda: no se publican noticias de encuestas.')
    pub = os.path.join(RAIZ, 'noticias', 'publicadas', f'{hoy.isoformat()}.json')
    if os.path.exists(pub) and not a.es_borrador:
        sys.exit('Ya hay una noticia publicada hoy.')

    faltan = [k for k in ('titulo', 'extracto', 'secciones', 'fichas', 'frase_clave', 'seo_descripcion') if not b.get(k)]
    if faltan:
        sys.exit('Faltan campos en el borrador: ' + ', '.join(faltan))
    if len(b['secciones']) != 3:
        sys.exit('La noticia debe tener exactamente 3 secciones (encuesta, tendencia, escenarios).')
    if len(b['seo_descripcion']) > 160:
        sys.exit(f'La meta descripción es demasiado larga ({len(b["seo_descripcion"])} caracteres; máximo 160).')

    img_rel = f'noticias/imagenes/{hoy.isoformat()}.png'
    r = subprocess.run([sys.executable, os.path.join(RAIZ, 'noticias', 'imagen.py'), '--salida', os.path.join(RAIZ, img_rel),
                        '--fecha', hoy.isoformat()] + (['--prueba'] if a.es_borrador else []),
                       capture_output=True, text=True)
    if r.returncode:
        sys.exit('Error al generar la imagen: ' + r.stderr)
    img = json.loads(r.stdout.strip().splitlines()[-1])

    partes = []
    for s in b['secciones']:
        partes.append(bloque_h2(s['subtitulo']))
        partes += [bloque_p(p) for p in s['parrafos']]
    partes.append(bloque_p(CIERRE))
    partes += [bloque_p(f) for f in b['fichas']]

    enc = slugify(b.get('encuestadora', 'encuesta'))
    out = {
        'fecha': hoy.isoformat(), 'estado': 'draft' if a.es_borrador else 'publish',
        'titulo': b['titulo'], 'slug': b.get('slug') or slugify(b['titulo']), 'extracto': b['extracto'],
        'contenido': '\n\n'.join(partes), 'categorias': [7041, 58], 'autor': 4,
        'etiquetas': b.get('etiquetas', []),
        'imagen': img_rel, 'imagen_alt': img['alt'],
        'imagen_nombre': f'encuesta-{enc}-29n-{hoy.day}-{MESES[hoy.month - 1]}.png',
        'seo': {'frase_clave': b['frase_clave'], 'titulo': b.get('seo_titulo', ''), 'descripcion': b['seo_descripcion'],
                'social_titulo': b.get('social_titulo', ''), 'social_descripcion': b.get('social_descripcion', ''),
                'categoria_principal': 7041},
        'tipo_imagen': img['tipo'],
    }
    os.makedirs(os.path.join(RAIZ, 'noticias', 'cola'), exist_ok=True)
    dest = os.path.join(RAIZ, 'noticias', 'cola', f'{hoy.isoformat()}.json')
    json.dump(out, open(dest, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    print(json.dumps({'cola': os.path.relpath(dest, RAIZ), 'imagen': img_rel, 'tipo_imagen': img['tipo'], 'estado': out['estado']}, ensure_ascii=False))


if __name__ == '__main__':
    main()

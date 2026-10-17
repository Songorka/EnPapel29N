#!/usr/bin/env python3
"""Imagen destacada diaria para la noticia de encuestas del 29N (Enpapel).

Uso:
  python3 noticias/imagen.py --salida /ruta/imagen.png [--fecha AAAA-MM-DD] [--tipo TIPO] [--prueba]

- Lee los datos de index.html (bloque JSON "datos").
- Elige un tipo de gráfico distinto al de los últimos días (noticias/historial.json).
- Garantiza que la imagen nunca es idéntica a una anterior (huella md5 en el historial).
- Imprime por pantalla un JSON con: tipo, variante, titular, alt, huella.
- Con --prueba no se escribe nada en el historial.
"""
import argparse, hashlib, io, json, math, os, re, sys
from datetime import date, timedelta
from PIL import Image, ImageDraw, ImageFont

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
AQUI = os.path.join(RAIZ, 'noticias')
HIST = os.path.join(AQUI, 'historial.json')
FUENTES = os.path.join(AQUI, 'fuentes')

S = 2
W, H = 1200 * S, 675 * S
GREEN = '#11512a'; PURPLE = '#4f3f93'; INK = '#151a2b'; INK2 = '#4a5068'; INK3 = '#7c8197'
LINE = '#e3e5ec'; BG = '#ffffff'; SOFT = '#f3f4f8'; UP = '#1d7a46'; DOWN = '#b3261e'
MESES = ['enero', 'febrero', 'marzo', 'abril', 'mayo', 'junio', 'julio', 'agosto', 'septiembre', 'octubre', 'noviembre', 'diciembre']
ORDEN = ['cara', 'hemiciclo', 'barras', 'encuesta', 'cambio23J', 'pactometro', 'tendencia']
PAREJAS = [('PP', 'PSOE'), ('PSOE', 'VOX'), ('PP', 'VOX'), ('SUMAR', 'PODEMOS')]
BLOQUE_DCHA = ['PP', 'VOX', 'UPN']
BLOQUE_INV = ['PSOE', 'SUMAR', 'PODEMOS', 'ERC', 'JUNTS', 'BILDU', 'PNV', 'BNG', 'CC']


def font(nombre, tam):
    return ImageFont.truetype(os.path.join(FUENTES, nombre), int(tam * S))


def fmt(v, dec=1):
    return f'{v:.{dec}f}'.replace('.', ',')


def fsig(v):
    return ('+' if v > 0 else '−' if v < 0 else '') + fmt(abs(v))


def texto_sobre(hexc):
    r, g, b = (int(hexc[i:i + 2], 16) for i in (1, 3, 5))
    return '#1a1a1a' if 0.299 * r + 0.587 * g + 0.114 * b > 165 else '#ffffff'


CON_ARTICULO = {'PP', 'PSOE', 'PNV', 'BNG'}


def art(c, k):
    """'el PP', 'el PSOE', 'Vox'…"""
    return ('el ' if k in CON_ARTICULO else '') + c.nombre(k)


def a_art(c, k):
    return 'al ' + c.nombre(k) if k in CON_ARTICULO else 'a ' + c.nombre(k)


def cap(t):
    return t[:1].upper() + t[1:]


def fecha_larga(d):
    return f'{d.day} de {MESES[d.month - 1]} de {d.year}'


# ---------------------------------------------------------------- datos
def cargar():
    h = open(os.path.join(RAIZ, 'index.html'), encoding='utf-8').read()
    return json.loads(re.search(r'<script type="application/json" id="datos">(.*?)</script>', h, re.S).group(1))


def d(s):
    return date.fromisoformat(s)


def media_hasta(polls, limite=None):
    """Misma regla que el panel: última encuesta de cada casa con fin de campo
    dentro de los 14 días anteriores a la más reciente."""
    # El CIS (o cualquier encuesta marcada fueraMedia) se muestra aparte y no entra en la media
    ps = [p for p in polls if (limite is None or d(p['published']) <= limite)
          and not (p.get('fueraMedia') or p['pollster'] == 'CIS')]
    if not ps:
        return {}, []
    ultimo = max(d(p['fieldEnd']) for p in ps)
    casa = {}
    for p in sorted(ps, key=lambda p: (d(p['fieldEnd']), d(p['published']))):
        e = d(p['fieldEnd'])
        if ultimo - timedelta(14) <= e <= ultimo:
            casa[p['pollster']] = p
    cur = list(casa.values())
    acc = {}
    for p in cur:
        for k, v in p['vote'].items():
            acc.setdefault(k, []).append(v)
    return {k: sum(a) / len(a) for k, a in acc.items()}, cur


def escanos(cur):
    mid = lambda v: (v[0] + v[1]) / 2 if isinstance(v, list) else v
    full = [p for p in cur if sum(mid(v) for v in (p.get('seats') or {}).values()) >= 340]
    if not full:
        return {}, 0
    sa = {}
    for p in full:
        for k, v in p['seats'].items():
            sa[k] = sa.get(k, 0) + mid(v) / len(full)
    tot = sum(sa.values())
    q = {k: v * 350 / tot for k, v in sa.items()}
    out = {k: int(v) for k, v in q.items()}
    for k in sorted(q, key=lambda k: q[k] - int(q[k]), reverse=True)[:350 - sum(out.values())]:
        out[k] += 1
    return out, len(full)


class Ctx:
    def __init__(self, D, hoy):
        self.D = D; self.P = D['parties']; self.hoy = hoy
        self.polls = sorted(D['polls'], key=lambda p: (d(p['published']), d(p['fieldEnd'])))
        self.media, self.cur = media_hasta(self.polls)
        self.esc, self.n_esc = escanos(self.cur)
        self.dias = (d(D['electionDate']) - hoy).days
        self.fechas = sorted({d(p['published']) for p in self.polls})

    def nombre(self, k):
        return self.P.get(k, {}).get('name', k)

    def color(self, k):
        return self.P.get(k, {}).get('color', '#888888')


# ---------------------------------------------------------------- lienzo común
_LOGO = None


def lienzo(c, etiqueta, titular, pie=None):
    global _LOGO
    if _LOGO is None:
        _LOGO = Image.open(os.path.join(RAIZ, 'logo-enpapel.png')).convert('RGBA')
    im = Image.new('RGB', (W, H), BG); dr = ImageDraw.Draw(im)
    lh = 54 * S; lw = int(_LOGO.width * lh / _LOGO.height)
    lg = _LOGO.resize((lw, lh), Image.LANCZOS)
    im.paste(lg, (56 * S, 40 * S), lg)
    x = 56 * S + lw + 16 * S
    dr.rectangle([x, 44 * S, x + 3 * S, 90 * S], fill=GREEN)
    dr.text((x + 16 * S, 67 * S), '29N', font=font('InterDisplay-Black.otf', 44), fill=GREEN, anchor='lm')
    dr.text((W - 56 * S, 54 * S), 'ELECCIONES GENERALES', font=font('Inter-SemiBold.otf', 15), fill=INK3, anchor='rm')
    sub = f'Faltan {c.dias} días · {fecha_larga(c.hoy)}' if c.dias > 1 else fecha_larga(c.hoy)
    dr.text((W - 56 * S, 80 * S), sub, font=font('Inter-Medium.otf', 17), fill=INK2, anchor='rm')
    dr.rectangle([56 * S, 112 * S, W - 56 * S, 115 * S], fill=INK)
    dr.text((56 * S, 150 * S), etiqueta.upper(), font=font('Inter-Bold.otf', 16), fill=PURPLE, anchor='lt')
    # titular: reduce tamaño si no cabe
    for tam in (50, 46, 42, 38, 34):
        f = font('InterDisplay-ExtraBold.otf', tam)
        if dr.textlength(titular, font=f) <= W - 112 * S:
            break
    dr.text((56 * S, 176 * S), titular, font=f, fill=INK, anchor='lt')
    dr.rectangle([0, H - 52 * S, W, H], fill=GREEN)
    pie = pie or f'Media de {len(c.cur)} encuestas publicadas · enpapel.es/encuestas-29n'
    dr.text((56 * S, H - 26 * S), pie, font=font('Inter-Medium.otf', 17), fill='#ffffff', anchor='lm')
    return im, dr


# ---------------------------------------------------------------- tipos
def t_cara(c, variante):
    a, b = variante.split('-')
    va, vb = c.media.get(a), c.media.get(b)
    if va is None or vb is None:
        return None
    lider, seg = (a, b) if va >= vb else (b, a)
    dif = abs(va - vb)
    titular = cap(f'{art(c, lider)} y {art(c, seg)}, prácticamente empatados' if dif < 0.5
                  else f'{art(c, lider)} saca {fmt(dif)} puntos {a_art(c, seg)}')
    im, dr = lienzo(c, 'Cara a cara', titular)
    y0 = 290 * S; cw = (W - 112 * S - 30 * S) // 2
    for i, k in enumerate((a, b)):
        v = c.media[k]; x0 = 56 * S + i * (cw + 30 * S); col = c.color(k); tc = texto_sobre(col)
        dr.rounded_rectangle([x0, y0, x0 + cw, y0 + 280 * S], radius=18 * S, fill=col)
        nom = 'Partido Popular' if k == 'PP' else c.nombre(k)
        dr.text((x0 + 34 * S, y0 + 30 * S), nom.upper(), font=font('Inter-Bold.otf', 22), fill=tc, anchor='lt')
        fb = font('InterDisplay-Black.otf', 150)
        dr.text((x0 + 30 * S, y0 + 150 * S), fmt(v), font=fb, fill=tc, anchor='lm')
        nb = dr.textbbox((x0 + 30 * S, y0 + 150 * S), fmt(v), font=fb, anchor='lm')
        dr.text((nb[2] + 10 * S, y0 + 120 * S), '%', font=font('InterDisplay-Bold.otf', 56), fill=tc, anchor='lm')
        if c.esc.get(k) is not None:
            dr.text((x0 + 34 * S, y0 + 240 * S), f'{c.esc[k]} escaños de media', font=font('Inter-SemiBold.otf', 22), fill=tc, anchor='lm')
    dr.ellipse([W // 2 - 34 * S, y0 + 106 * S, W // 2 + 34 * S, y0 + 174 * S], fill=BG, outline=INK, width=3 * S)
    dr.text((W // 2, y0 + 140 * S), 'vs', font=font('InterDisplay-Black.otf', 28), fill=INK, anchor='mm')
    alt = f'Cara a cara: {c.nombre(a)} {fmt(va)} % frente a {c.nombre(b)} {fmt(vb)} % en la media de encuestas'
    return im, titular, alt


def t_hemiciclo(c, variante):
    if not c.esc:
        return None
    s = c.esc
    dcha = sum(s.get(k, 0) for k in BLOQUE_DCHA); inv = sum(s.get(k, 0) for k in BLOQUE_INV)
    titular = ('PP y Vox sumarían mayoría absoluta' if s.get('PP', 0) + s.get('VOX', 0) >= 176
               else 'El bloque de investidura retendría la mayoría' if inv >= 176
               else 'Ningún bloque llega a la mayoría absoluta')
    im, dr = lienzo(c, 'Reparto de escaños', titular, f'Media de {c.n_esc} encuestas con reparto completo · enpapel.es/encuestas-29n')
    orden = sorted(c.P, key=lambda k: c.P[k].get('seatOrder', 99))
    cx, cy = 400 * S, 590 * S; R0, R1 = 130 * S, 330 * S; filas = 10
    radios = [R0 + (R1 - R0) * i / (filas - 1) for i in range(filas)]
    tl = sum(radios); cuenta = [round(350 * r / tl) for r in radios]; cuenta[-1] += 350 - sum(cuenta)
    pts = [(math.pi * (1 - j / (n - 1)), r) for r, n in zip(radios, cuenta) for j in range(n)]
    pts.sort(key=lambda t: (-t[0], t[1]))
    seq = [k for k in orden for _ in range(s.get(k, 0))]; seq += [None] * (350 - len(seq))
    rd = 7.2 * S
    for (a, r), k in zip(pts, seq):
        x, y = cx + r * math.cos(a), cy - r * math.sin(a)
        dr.ellipse([x - rd, y - rd, x + rd, y + rd], fill=c.color(k) if k else LINE)
    dr.text((cx, cy - 60 * S), '350', font=font('InterDisplay-Black.otf', 54), fill=INK, anchor='mm')
    dr.text((cx, cy - 20 * S), 'mayoría: 176', font=font('Inter-Medium.otf', 18), fill=INK3, anchor='mm')
    lx, ly = 790 * S, 250 * S
    for lab, val, col in [('PP + Vox + UPN', dcha, c.color('PP')), ('Bloque de investidura', inv, c.color('PSOE'))]:
        dr.text((lx, ly), lab, font=font('Inter-SemiBold.otf', 20), fill=INK2, anchor='lt')
        dr.text((lx, ly + 28 * S), str(val), font=font('InterDisplay-Black.otf', 64), fill=col, anchor='lt')
        ly += 112 * S
    ly += 6 * S
    peq = [k for k in sorted(s, key=lambda k: -s[k]) if s[k]][:6]
    for i, k in enumerate(peq):
        x = lx + (i % 2) * 175 * S; y = ly + (i // 2) * 32 * S
        dr.rounded_rectangle([x, y, x + 16 * S, y + 16 * S], radius=4 * S, fill=c.color(k))
        dr.text((x + 24 * S, y + 8 * S), f'{c.nombre(k)} {s[k]}', font=font('Inter-Medium.otf', 18), fill=INK, anchor='lm')
    alt = f'Hemiciclo con la media de escaños: PP, Vox y UPN {dcha}; bloque de investidura {inv}; mayoría absoluta 176'
    return im, titular, alt


def barras_h(dr, c, filas, x0, y0, ancho, alto_fila, maximo, marcas=None):
    """filas: [(clave, valor)] ; marcas: {clave: valor de referencia}"""
    fe = font('Inter-Bold.otf', 19); fv = font('InterDisplay-Bold.otf', 24)
    ax = x0 + 150 * S; aw = ancho - 150 * S - 100 * S
    for i, (k, v) in enumerate(filas):
        y = y0 + i * alto_fila; col = c.color(k); h = alto_fila * 0.56
        dr.text((x0, y + h / 2), c.nombre(k), font=fe, fill=INK, anchor='lm')
        dr.rounded_rectangle([ax, y, ax + aw, y + h], radius=6 * S, fill=SOFT)
        dr.rounded_rectangle([ax, y, ax + max(h, aw * v / maximo), y + h], radius=6 * S, fill=col)
        if marcas and marcas.get(k) is not None:
            mx = ax + aw * marcas[k] / maximo
            dr.line([mx, y - 5 * S, mx, y + h + 5 * S], fill=INK, width=3 * S)
        dr.text((ax + aw + 18 * S, y + h / 2), fmt(v) + ' %', font=fv, fill=INK, anchor='lm')


def t_barras(c, variante):
    filas = sorted([(k, v) for k, v in c.media.items() if v >= 1.0], key=lambda t: -t[1])[:9]
    if len(filas) < 4:
        return None
    k1, v1 = filas[0]; k2, v2 = filas[1]
    titular = cap(art(c, k1)) + f' lidera con el {fmt(v1)} % de la intención de voto'
    im, dr = lienzo(c, 'Estimación de voto', titular)
    alto = min(46 * S, (H - 52 * S - 270 * S) // len(filas))
    barras_h(dr, c, filas, 56 * S, 262 * S, W - 112 * S, alto, filas[0][1] * 1.05)
    alt = 'Barras con la media de estimación de voto: ' + ', '.join(f'{c.nombre(k)} {fmt(v)} %' for k, v in filas)
    return im, titular, alt


def t_encuesta(c, variante):
    p = next((p for p in c.polls if p['id'] == variante), None)
    if not p:
        return None
    filas = sorted([(k, v) for k, v in p['vote'].items() if v >= 1.0], key=lambda t: -t[1])[:7]
    quien = p['pollster'].rstrip('.')
    medio = f' para {p["media"]}' if p.get('media') else ''
    titular = f'{quien}{medio}: ' + ', '.join(f'{c.nombre(k)} {fmt(v)}' for k, v in filas[:2])
    im, dr = lienzo(c, 'La última encuesta', titular,
                    f'{quien}{medio} · publicada el {d(p["published"]).day} de {MESES[d(p["published"]).month - 1]} · la raya negra marca la media')
    alto = min(50 * S, (H - 52 * S - 270 * S) // len(filas))
    barras_h(dr, c, filas, 56 * S, 262 * S, W - 112 * S, alto, filas[0][1] * 1.08, marcas=c.media)
    alt = f'Encuesta de {quien}{medio}: ' + ', '.join(f'{c.nombre(k)} {fmt(v)} %' for k, v in filas) + '. Se compara con la media.'
    return im, titular, alt


def t_cambio23J(c, variante):
    R = c.D.get('results2023', {}).get('vote', {})
    if not R:
        return None
    m = dict(c.media)
    if 'PODEMOS' in m:  # en 2023 Podemos fue dentro de Sumar
        m['SUMAR+'] = m.get('SUMAR', 0) + m.pop('PODEMOS'); m.pop('SUMAR', None)
        R = dict(R); R['SUMAR+'] = R.pop('SUMAR', 0)
    claves = [k for k in ['PP', 'PSOE', 'VOX', 'SUMAR+', 'ERC', 'JUNTS', 'BILDU', 'PNV'] if k in m and k in R]
    dif = {k: m[k] - R[k] for k in claves}
    top = max(dif, key=lambda k: abs(dif[k]))
    nom = lambda k: 'Sumar + Podemos' if k == 'SUMAR+' else c.nombre(k)
    verbo = 'gana' if dif[top] > 0 else 'pierde'
    titular = cap('Sumar y Podemos juntos' if top == 'SUMAR+' else art(c, top)) + f' {verbo} {fmt(abs(dif[top]))} puntos desde el 23J'
    im, dr = lienzo(c, 'Cambio desde las elecciones de 2023', titular, 'Media de encuestas frente al resultado del 23 de julio de 2023 · enpapel.es/encuestas-29n')
    cx = W // 2 + 60 * S; esc = (W // 2 - 220 * S) / max(abs(v) for v in dif.values())
    y0 = 262 * S; alto = min(46 * S, (H - 52 * S - 270 * S) // len(claves))
    dr.line([cx, y0 - 10 * S, cx, y0 + alto * len(claves)], fill=INK3, width=2 * S)
    fe = font('Inter-Bold.otf', 19); fv = font('InterDisplay-Bold.otf', 22)
    for i, k in enumerate(claves):
        y = y0 + i * alto; h = alto * 0.56; v = dif[k]
        col = c.color('SUMAR' if k == 'SUMAR+' else k)
        dr.text((56 * S, y + h / 2), nom(k), font=fe, fill=INK, anchor='lm')
        x1 = cx + v * esc
        dr.rounded_rectangle([min(cx, x1), y, max(cx, x1) + 1, y + h], radius=5 * S, fill=col)
        dr.text((x1 + (14 * S if v >= 0 else -14 * S), y + h / 2), fsig(v), font=fv,
                fill=UP if v > 0 else DOWN if v < 0 else INK3, anchor='lm' if v >= 0 else 'rm')
    alt = 'Diferencia entre la media de encuestas y el resultado de 2023: ' + ', '.join(f'{nom(k)} {fsig(dif[k])} puntos' for k in claves)
    return im, titular, alt


def t_pactometro(c, variante):
    if not c.esc:
        return None
    s = c.esc
    combos = [
        ('PP + Vox', ['PP', 'VOX']),
        ('PP + Vox + UPN + CC', ['PP', 'VOX', 'UPN', 'CC']),
        ('Bloque de investidura', BLOQUE_INV),
        ('Investidura sin Junts', [k for k in BLOQUE_INV if k != 'JUNTS']),
        ('PP + PSOE', ['PP', 'PSOE']),
    ]
    tot = {lab: sum(s.get(k, 0) for k in ks) for lab, ks in combos}
    ok = [lab for lab in tot if tot[lab] >= 176 and lab != 'PP + PSOE']
    titular = (f'Solo {ok[0]} supera los 176 escaños' if len(ok) == 1 else
               f'{len(ok)} combinaciones superan la mayoría' if ok else 'Ninguna suma llega a 176 escaños')
    if ok and ok[0] == 'PP + Vox':
        titular = f'PP y Vox suman {tot["PP + Vox"]} escaños: mayoría absoluta'
    im, dr = lienzo(c, 'Pactómetro', titular, f'Media de {c.n_esc} encuestas con reparto completo · enpapel.es/encuestas-29n')
    x0 = 56 * S; ax = x0 + 300 * S; aw = W - 56 * S - ax - 90 * S; y0 = 262 * S; alto = 62 * S
    fe = font('Inter-Bold.otf', 19); fv = font('InterDisplay-Black.otf', 26)
    for i, (lab, ks) in enumerate(combos):
        y = y0 + i * alto; h = 34 * S; x = ax
        dr.text((x0, y + h / 2), lab, font=fe, fill=INK, anchor='lm')
        dr.rounded_rectangle([ax, y, ax + aw, y + h], radius=6 * S, fill=SOFT)
        for k in sorted(ks, key=lambda k: -s.get(k, 0)):
            wv = aw * s.get(k, 0) / 350
            if wv > 0:
                dr.rectangle([x, y, x + wv, y + h], fill=c.color(k)); x += wv
        dr.text((ax + aw + 16 * S, y + h / 2), str(tot[lab]), font=fv, fill=UP if tot[lab] >= 176 else INK, anchor='lm')
    mx = ax + aw * 176 / 350
    dr.line([mx, y0 - 22 * S, mx, y0 + alto * len(combos) - 20 * S], fill=INK, width=3 * S)
    dr.text((mx, y0 - 26 * S), '176', font=font('Inter-Bold.otf', 16), fill=INK, anchor='mb')
    alt = 'Pactómetro con la media de escaños: ' + ', '.join(f'{lab} {tot[lab]}' for lab in tot) + '. Mayoría absoluta 176.'
    return im, titular, alt


def t_tendencia(c, variante):
    serie = []
    for f in c.fechas:
        m, _ = media_hasta(c.polls, f)
        serie.append((f, m))
    if len(serie) < 3:
        return None
    partidos = [k for k, _ in sorted(c.media.items(), key=lambda t: -t[1])[:4]]
    cambio = {k: serie[-1][1].get(k, 0) - serie[0][1].get(k, 0) for k in partidos}
    top = max(cambio, key=lambda k: abs(cambio[k]))
    desde = f'{serie[0][0].day} de {MESES[serie[0][0].month - 1]}'
    titular = (cap(art(c, top)) + f' {"sube" if cambio[top] > 0 else "baja"} {fmt(abs(cambio[top]))} puntos desde el {desde}'
               if abs(cambio[top]) >= 0.3 else f'La media apenas se mueve desde el {desde}')
    im, dr = lienzo(c, 'Evolución de la media', titular)
    gx0, gx1, gy0, gy1 = 110 * S, W - 230 * S, 262 * S, H - 100 * S
    vals = [m.get(k) for _, m in serie for k in partidos if m.get(k) is not None]
    lo, hi = math.floor(min(vals) / 5) * 5, math.ceil(max(vals) / 5) * 5
    Y = lambda v: gy1 - (v - lo) / (hi - lo) * (gy1 - gy0)
    t0, t1 = serie[0][0], serie[-1][0]; span = max(1, (t1 - t0).days)
    X = lambda f: gx0 + (f - t0).days / span * (gx1 - gx0)
    fa = font('Inter-Medium.otf', 16)
    for v in range(lo, hi + 1, 5):
        dr.line([gx0, Y(v), gx1, Y(v)], fill=LINE, width=2 * S)
        dr.text((gx0 - 14 * S, Y(v)), f'{v} %', font=fa, fill=INK3, anchor='rm')
    for f in (t0, t1):
        dr.text((X(f), gy1 + 16 * S), f'{f.day} {MESES[f.month - 1][:3]}', font=fa, fill=INK3, anchor='mt')
    etiquetas = []
    for k in partidos:
        pts = [(X(f), Y(m[k])) for f, m in serie if m.get(k) is not None]
        dr.line(pts, fill=c.color(k), width=6 * S, joint='curve')
        for x, y in pts:
            dr.ellipse([x - 7 * S, y - 7 * S, x + 7 * S, y + 7 * S], fill=c.color(k))
        etiquetas.append([pts[-1][1], k])
    etiquetas.sort()
    for i in range(1, len(etiquetas)):  # separa etiquetas solapadas
        etiquetas[i][0] = max(etiquetas[i][0], etiquetas[i - 1][0] + 30 * S)
    for y, k in etiquetas:
        dr.text((gx1 + 20 * S, y), f'{c.nombre(k)} {fmt(c.media[k])}', font=font('Inter-Bold.otf', 20), fill=c.color(k), anchor='lm')
    alt = f'Evolución de la media de encuestas desde el {desde}: ' + ', '.join(f'{c.nombre(k)} {fsig(cambio[k])} puntos' for k in partidos)
    return im, titular, alt


TIPOS = {'cara': t_cara, 'hemiciclo': t_hemiciclo, 'barras': t_barras, 'encuesta': t_encuesta,
         'cambio23J': t_cambio23J, 'pactometro': t_pactometro, 'tendencia': t_tendencia}


# ---------------------------------------------------------------- elección
def candidatos(c, hist):
    """Lista ordenada de (tipo, variante) a probar."""
    recientes = [h['tipo'] for h in hist[-4:]]
    usados_enc = {h['variante'] for h in hist if h['tipo'] == 'encuesta'}
    caras = [h['variante'] for h in hist if h['tipo'] == 'cara']
    sig_pareja = 0
    if caras and caras[-1] in ['-'.join(p) for p in PAREJAS]:
        sig_pareja = (['-'.join(p) for p in PAREJAS].index(caras[-1]) + 1) % len(PAREJAS)
    parejas = ['-'.join(PAREJAS[(sig_pareja + i) % len(PAREJAS)]) for i in range(len(PAREJAS))]
    ultima = c.polls[-1]['id'] if c.polls else None

    def variantes(t):
        if t == 'cara':
            return parejas
        if t == 'encuesta':
            return [p['id'] for p in reversed(c.polls) if p['id'] not in usados_enc][:3]
        return ['']

    # orden de tipos: empieza después del último usado
    ini = (ORDEN.index(hist[-1]['tipo']) + 1) % len(ORDEN) if hist and hist[-1]['tipo'] in ORDEN else 0
    rot = [ORDEN[(ini + i) % len(ORDEN)] for i in range(len(ORDEN))]
    # una encuesta nueva sin contar tiene prioridad, si no salió ese tipo en los últimos 2 días
    if ultima and ultima not in usados_enc and 'encuesta' not in recientes[-2:]:
        rot.remove('encuesta'); rot.insert(0, 'encuesta')
    frescos = [t for t in rot if t not in recientes]
    resto = [t for t in rot if t in recientes]
    return [(t, v) for t in frescos + resto for v in variantes(t)]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--salida', required=True)
    ap.add_argument('--fecha')
    ap.add_argument('--tipo')
    ap.add_argument('--variante', default=None)
    ap.add_argument('--prueba', action='store_true')
    a = ap.parse_args()
    hoy = d(a.fecha) if a.fecha else date.today()
    c = Ctx(cargar(), hoy)
    hist = json.load(open(HIST)) if os.path.exists(HIST) else []
    huellas = {h['huella'] for h in hist}
    if a.tipo:
        cands = [(a.tipo, a.variante if a.variante is not None else (PAREJAS[0] and '-'.join(PAREJAS[0]) if a.tipo == 'cara'
                 else c.polls[-1]['id'] if a.tipo == 'encuesta' else ''))]
    else:
        cands = candidatos(c, hist)
    for tipo, var in cands:
        r = TIPOS[tipo](c, var)
        if not r:
            continue
        im, titular, alt = r
        im = im.resize((1200, 675), Image.LANCZOS)
        buf = io.BytesIO(); im.save(buf, 'PNG', optimize=True)
        huella = hashlib.md5(buf.getvalue()).hexdigest()
        if huella in huellas and not a.tipo:
            continue  # nunca repetir una imagen idéntica
        open(a.salida, 'wb').write(buf.getvalue())
        reg = {'fecha': hoy.isoformat(), 'tipo': tipo, 'variante': var, 'titular': titular, 'alt': alt, 'huella': huella}
        if not a.prueba:
            hist.append(reg)
            json.dump(hist, open(HIST, 'w'), ensure_ascii=False, indent=1)
        print(json.dumps(reg, ensure_ascii=False))
        return
    sys.exit('No se ha podido generar ninguna imagen nueva')


if __name__ == '__main__':
    main()

#!/usr/bin/env python3
"""Vídeo semanal de encuestas 29N (vertical 1080x1920). Todas las cifras salen de datos.json.
Uso: python3 render.py guion.json salida.mp4"""
import json, math, subprocess, sys, wave
import numpy as np
from PIL import Image, ImageDraw, ImageFont

W, H, FPS = 1080, 1920, 30
BASE = '/home/claude/video'
FUENTES = '/home/claude/enpapel29n/noticias/fuentes'
CREMA, TINTA, TINTA2, VERDE, MORADO, LINEA = (247, 243, 232), (21, 26, 43), (74, 80, 104), (17, 81, 42), (79, 63, 147), (221, 214, 196)

def F(nombre, tam): return ImageFont.truetype(f'{FUENTES}/{nombre}.otf', tam)
f_eyebrow, f_fecha = F('Inter-Bold', 30), F('Inter-SemiBold', 36)
f_titulo, f_sub = F('InterDisplay-ExtraBold', 64), F('Inter-SemiBold', 50)
f_valor, f_badge, f_pie = F('InterDisplay-ExtraBold', 60), F('InterDisplay-Bold', 34), F('Inter-Medium', 26)
f_gigante, f_grande, f_medio = F('InterDisplay-Black', 380), F('InterDisplay-Black', 150), F('InterDisplay-Bold', 44)

G = json.load(open(sys.argv[1], encoding='utf-8'))
DAT = json.load(open(f'{BASE}/datos.json', encoding='utf-8'))
P = DAT['parties']
def col(k): h = P[k]['color'].lstrip('#'); return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))
def txtcol(c): return (26, 26, 26) if 0.299 * c[0] + 0.587 * c[1] + 0.114 * c[2] > 165 else (255, 255, 255)
NOMBRE = {'PP': 'PP', 'PSOE': 'PSOE', 'VOX': 'Vox', 'SUMAR': 'Sumar', 'PODEMOS': 'Podemos'}
def num(v, dec=1): return f'{v:.{dec}f}'.replace('.', ',')

def ease(x): x = max(0.0, min(1.0, x)); return 1 - (1 - x) ** 3
def pop(x):  # rebote al aparecer
    x = max(0.0, min(1.0, x)); return 1 + 0.12 * math.sin(math.pi * x) * (1 - x) if x < 1 else 1.0

# ---------- audio: une los clips con pausas y calcula tiempos ----------
SR = 44100
def leer(ruta):
    w = wave.open(ruta); n = w.getnframes(); sr = w.getframerate(); ch = w.getnchannels()
    x = np.frombuffer(w.readframes(n), dtype=np.int16).astype(np.float32)
    if ch > 1: x = x.reshape(-1, ch).mean(1)
    if sr != SR: x = np.interp(np.arange(0, len(x), sr / SR), np.arange(len(x)), x)
    return x
pistas, t, escenas = [np.zeros(int(SR * G['entrada']))], G['entrada'], []
for esc in G['escenas']:
    ini = t; clips = []
    for c in esc['clips']:
        x = leer(f"{BASE}/audio/{c['audio']}")
        clips.append({'ini': t, 'fin': t + len(x) / SR, 'texto': c['texto'], 'x': x})
        pistas += [x, np.zeros(int(SR * G['pausa']))]; t += len(x) / SR + G['pausa']
    escenas.append({**esc, 'ini': ini, 'fin': t, 'clips': clips})
pistas.append(np.zeros(int(SR * G['salida']))); t += G['salida']
audio = np.concatenate(pistas); TOTAL = t
audio = audio / max(1, np.abs(audio).max()) * 0.92 * 32767
wv = wave.open(f'{BASE}/narracion.wav', 'w'); wv.setnchannels(1); wv.setsampwidth(2); wv.setframerate(SR)
wv.writeframes(audio.astype(np.int16).tobytes()); wv.close()
spf = SR // FPS
rms = np.array([np.sqrt(np.mean((audio[i * spf:(i + 1) * spf] / 32767) ** 2)) if i * spf < len(audio) else 0 for i in range(int(TOTAL * FPS) + 2)])
rms = np.convolve(rms / max(rms.max(), 1e-6), np.ones(3) / 3, 'same')

# subtítulos: frases repartidas por longitud dentro de cada clip
subs = []
for e in escenas:
    for c in e['clips']:
        import re
        frases = [f.strip() for f in re.split(r'(?<=[.?!])\s+', c['texto']) if f.strip()]
        tot = sum(len(f) for f in frases); a = c['ini']
        for f in frases:
            b = a + (c['fin'] - c['ini']) * len(f) / tot; subs.append((a, b, f)); a = b

# ---------- recursos ----------
logo = Image.open(f'{BASE}/logo.png').convert('RGBA'); logo = logo.resize((int(logo.width * 96 / logo.height), 96), Image.LANCZOS)
SPR = {}
for k in ('neutral', 'explica', 'sorpresa', 'piensa', 'adios'):
    im = Image.open(f'{BASE}/sprites/{k}.png').convert('RGBA'); bb = im.getbbox(); im = im.crop(bb)
    SPR[k] = im.resize((int(im.width * 560 / im.height), 560), Image.LANCZOS)

def centrado(dr, x, y, s, f, fill):
    w = dr.textlength(s, font=f); dr.text((x - w / 2, y), s, font=f, fill=fill)

def badge(dr, x, y, k, f=f_badge, h=58):
    c = col(k); s = NOMBRE.get(k, k).upper(); w = dr.textlength(s, font=f) + 36
    dr.rounded_rectangle((x, y, x + w, y + h), 12, fill=c); dr.text((x + 18, y + (h - f.size) / 2 - 4), s, font=f, fill=txtcol(c))
    return w

def envolver(dr, s, f, ancho):
    lin, cur = [], ''
    for p in s.split():
        prueba = (cur + ' ' + p).strip()
        if dr.textlength(prueba, font=f) <= ancho: cur = prueba
        else: lin.append(cur); cur = p
    return lin + [cur]

def titulo(dr, s, a):
    dr.text((60, 330), s, font=f_titulo, fill=TINTA + (int(255 * a),) if False else TINTA)

# ---------- escenas ----------
def e_gancho(dr, img, lt, e):
    n = int(round(7 * ease(lt / 1.0)))
    centrado(dr, W / 2, 300, str(n), f_gigante, VERDE)
    centrado(dr, W / 2, 720, 'encuestas nuevas', f_titulo, TINTA)
    centrado(dr, W / 2, 800, 'esta semana', f_sub, TINTA2)
    casas = G['casas']; x, y = 70, 930
    for i, c in enumerate(casas):
        a = ease((lt - 0.4 - i * 0.22) / 0.3)
        if a <= 0: continue
        w = dr.textlength(c, font=f_medio) + 48
        if x + w > W - 70: x, y = 70, y + 92
        fill = (233, 226, 242) if c == 'CIS' else (226, 238, 224)
        dr.rounded_rectangle((x, y + (1 - a) * 30, x + w, y + 74 + (1 - a) * 30), 37, fill=fill)
        dr.text((x + 24, y + 12 + (1 - a) * 30), c, font=f_medio, fill=TINTA); x += w + 16

def e_media(dr, img, lt, e):
    dr.text((60, 330), 'La media de las encuestas', font=f_titulo, fill=TINTA)
    dr.text((60, 410), 'Sin el CIS · ' + G['n_casas'] + ' encuestadoras', font=f_fecha, fill=TINTA2)
    filas = G['filas_media']; y0 = 520; maxv = 40
    for i, (k, t0) in enumerate(filas):
        a = ease((lt - t0) / 0.9)
        if lt < t0 - 0.05: continue
        y = y0 + i * 140; v = DAT['vote'][k] * a
        badge(dr, 60, y, k); bx0, bx1 = 330, 960
        dr.rounded_rectangle((bx0, y + 6, bx1, y + 52), 23, fill=(236, 230, 214))
        dr.rounded_rectangle((bx0, y + 6, bx0 + max(46, (bx1 - bx0) * v / maxv), y + 52), 23, fill=col(k))
        dr.text((bx0, y + 62), num(v) + ' %', font=f_medio, fill=TINTA)

ORDEN_HEMI = sorted(DAT['seats'], key=lambda k: P[k]['seatOrder'])
def puntos_hemiciclo():
    cx, cy, filas, r0, r1, pts = W / 2, 960, 11, 150, 430, []
    radios = [r0 + (r1 - r0) * i / (filas - 1) for i in range(filas)]
    cuentas = [round(350 * r / sum(radios)) for r in radios]; cuentas[-1] += 350 - sum(cuentas)
    for r, n in zip(radios, cuentas):
        for j in range(n):
            a = math.pi * (1 - (j + .5) / n); pts.append((a, cx + r * math.cos(a), cy - r * math.sin(a)))
    pts.sort(key=lambda p: -p[0]); return pts
PTS = puntos_hemiciclo()
DOTS = [k for k in ORDEN_HEMI for _ in range(DAT['seats'][k])]
def e_escanos(dr, img, lt, e):
    dr.text((60, 330), 'Los escaños', font=f_titulo, fill=TINTA)
    dr.text((60, 410), 'Media de las encuestas con reparto completo', font=f_fecha, fill=TINTA2)
    lleno = int(350 * ease(lt / 2.2)); resalta = lt > G['t_resalta']
    dcha = {'PP', 'VOX', 'UPN'}
    for i, (a, x, y) in enumerate(PTS):
        if i >= lleno: continue
        c = col(DOTS[i])
        if resalta and DOTS[i] not in dcha: c = tuple(int(v * .25 + 236 * .75) for v in c)
        dr.ellipse((x - 10, y - 10, x + 10, y + 10), fill=c)
    dr.line((W / 2, 960 - 450, W / 2, 960 - 140), fill=TINTA, width=4)
    centrado(dr, W / 2, 462, 'mayoría · 176', f_fecha, TINTA)
    if resalta:
        a = ease((lt - G['t_resalta']) / 0.6)
        n = int(round(G['pp_vox'] * a)); centrado(dr, W / 2, 975, str(n), f_grande.font_variant(size=120), VERDE)
        centrado(dr, W / 2, 1115, 'escaños de PP + Vox (con UPN)', f_fecha, TINTA)

def tarjeta(dr, x, y, w, h, titulo_, filas, nota, a, morado=False):
    off = (1 - a) * 60
    dr.rounded_rectangle((x, y + off, x + w, y + h + off), 28, fill=(255, 255, 255), outline=MORADO if morado else LINEA, width=4)
    dr.text((x + 34, y + 28 + off), titulo_, font=f_titulo, fill=TINTA)
    yy = y + 120 + off
    for k, v in filas:
        badge(dr, x + 34, yy, k); dr.text((x + 270, yy - 6), num(v) + ' %', font=f_valor, fill=TINTA); yy += 86
    dr.text((x + 34, yy + 8), nota, font=f_fecha, fill=MORADO if morado else VERDE)

def e_discordante(dr, img, lt, e):
    dr.text((60, 330), 'Las que se salen del guion', font=f_titulo, fill=TINTA)
    a = ease((lt - G['t_gesop']) / 0.5)
    if a > 0: tarjeta(dr, 60, 440, 960, 370, 'GESOP', [('PP', G['gesop']['PP']), ('PSOE', G['gesop']['PSOE'])], 'Solo 2,6 puntos de diferencia', a)
    b = ease((lt - G['t_cis']) / 0.5)
    if b > 0: tarjeta(dr, 60, 850, 960, 370, 'CIS', [('PSOE', G['cis']['PSOE']), ('PP', G['cis']['PP'])], 'Fuera de nuestra media', b, morado=True)

def barra_bloque(dr, y, etiqueta, valor, color, a=1.0):
    x0, x1, maxv = 60, 1020, 260
    dr.text((x0, y), etiqueta, font=f_medio, fill=TINTA)
    dr.rounded_rectangle((x0, y + 60, x1, y + 130), 20, fill=(236, 230, 214))
    dr.rounded_rectangle((x0, y + 60, x0 + (x1 - x0) * valor / maxv * a, y + 130), 20, fill=color)
    s = str(int(round(valor))); dr.text((x1 - dr.textlength(s, font=f_valor) - 20, y + 64), s, font=f_valor, fill=TINTA)
def e_vuelta(dr, img, lt, e):
    dr.text((60, 330), '¿Puede darse la vuelta?', font=f_titulo, fill=TINTA)
    c2, c3 = e['clips'][1]['ini'] - e['ini'], e['clips'][2]['ini'] - e['ini']
    mov = 30 * ease((lt - c2 - 0.3) / 2.5)
    barra_bloque(dr, 460, 'PP + Vox', G['pp_vox'] - mov, col('PP'), ease(lt / 0.8))
    barra_bloque(dr, 640, 'Bloque de la investidura de 2023', G['investidura'] + mov, col('PSOE'), ease(lt / 0.8))
    xm = 60 + 960 * 176 / 260
    for y0_ in (520, 700):
        for yy in range(y0_, y0_ + 80, 20): dr.line((xm, yy, xm, yy + 10), fill=TINTA, width=4)
    centrado(dr, xm, 800, '176', f_medio, TINTA)
    if lt > c2 + 0.3:
        a = ease((lt - c2 - 0.3) / 0.5)
        dr.rounded_rectangle((60, 880, 1020, 1010), 26, fill=(226, 238, 224))
        centrado(dr, W / 2, 905, '≈ 7 de cada 100 votantes', f_medio, VERDE)
        centrado(dr, W / 2, 958, 'cambiando de bloque en 6 semanas', f_fecha, TINTA2)
    if lt > c3:
        a = ease((lt - c3) / 0.8)
        barra_bloque(dr, 1040, '¿Pacto PP + PSOE?', G['pp_psoe'] * a, (140, 140, 160), 1.0)

def e_cierre(dr, img, lt, e):
    centrado(dr, W / 2, 380, 'Faltan', f_titulo, TINTA2)
    centrado(dr, W / 2, 450, str(G['dias']), f_gigante, VERDE)
    centrado(dr, W / 2, 860, 'días para el 29N', f_titulo, TINTA)
    a = ease((lt - 3.6) / 0.6)
    if a > 0:
        centrado(dr, W / 2, 990, 'Todas las encuestas y el pactómetro', f_fecha, TINTA2)
        s = 'enpapel.es/encuestas-29n'; w = dr.textlength(s, font=f_medio) + 70
        dr.rounded_rectangle((W / 2 - w / 2, 1050, W / 2 + w / 2, 1140), 45, fill=VERDE)
        centrado(dr, W / 2, 1066, s, f_medio, (255, 255, 255))

ESC = {'gancho': e_gancho, 'media': e_media, 'escanos': e_escanos, 'discordante': e_discordante, 'vuelta': e_vuelta, 'cierre': e_cierre}

# ---------- fotograma ----------
def fotograma(i):
    t = i / FPS
    img = Image.new('RGBA', (W, H), CREMA + (255,)); dr = ImageDraw.Draw(img)
    dr.rectangle((0, 0, W, 14), fill=VERDE)
    img.alpha_composite(logo, (60, 60))
    s = '29N'; dr.text((W - 60 - dr.textlength(s, font=f_grande.font_variant(size=110)), 46), s, font=f_grande.font_variant(size=110), fill=VERDE)
    dr.text((60, 190), 'LAS ENCUESTAS DE LA SEMANA', font=f_eyebrow, fill=TINTA2)
    dr.text((60, 232), G['fecha'], font=f_fecha, fill=TINTA)
    dr.line((60, 296, W - 60, 296), fill=TINTA, width=3)
    esc = next((e for e in escenas if e['ini'] <= t < e['fin']), escenas[-1] if t >= escenas[-1]['ini'] else escenas[0])
    lt = t - esc['ini']
    ESC[esc['tipo']](dr, img, lt, esc)
    # personaje: balanceo + "habla" con la voz
    spr = SPR[esc['pose']]; r = rms[min(i, len(rms) - 1)]
    sy = 1 + 0.035 * r; sx = 1 - 0.012 * r
    sp = spr.resize((int(spr.width * sx), int(spr.height * sy)), Image.BILINEAR).rotate(2.2 * math.sin(t * 2.1), resample=Image.BICUBIC, expand=True)
    bob = 8 * math.sin(t * 3.0)
    img.alpha_composite(sp, (int(40 + (spr.width - sp.width) / 2), int(1235 + 560 - sp.height + bob)))
    # subtítulo
    sub = next((s for s in subs if s[0] <= t < s[1] + 0.15), None)
    if sub:
        x0, x1 = 450, 1040
        lin = envolver(dr, sub[2], f_sub, x1 - x0 - 60)
        hh = len(lin) * 64 + 50; y0 = 1520 - hh / 2
        dr.rounded_rectangle((x0, y0, x1, y0 + hh), 30, fill=(255, 255, 255), outline=LINEA, width=3)
        for j, l in enumerate(lin): dr.text((x0 + 30, y0 + 22 + j * 64), l, font=f_sub, fill=TINTA)
    # pie
    dr.line((60, 1812, W - 60, 1812), fill=LINEA, width=2)
    dr.text((60, 1830), 'Personaje animado con IA · Media de encuestas publicadas (sin el CIS),', font=f_pie, fill=TINTA2)
    dr.text((60, 1866), 'elaborada por Enpapel · enpapel.es/encuestas-29n', font=f_pie, fill=TINTA2)
    return img.convert('RGB')

if __name__ == '__main__':
    salida = sys.argv[2]
    if len(sys.argv) > 3:  # modo prueba: fotogramas sueltos
        for s in sys.argv[3].split(','):
            fotograma(int(float(s) * FPS)).save(f'{salida}_{s}.png')
        print('duración', round(TOTAL, 1), [(e['tipo'], round(e['ini'], 1)) for e in escenas]); sys.exit()
    n = int(TOTAL * FPS)
    ff = subprocess.Popen(['ffmpeg', '-loglevel', 'error', '-y', '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-s', f'{W}x{H}', '-r', str(FPS), '-i', '-',
                           '-i', f'{BASE}/narracion.wav', '-c:v', 'libx264', '-preset', 'medium', '-crf', '20', '-pix_fmt', 'yuv420p',
                           '-c:a', 'aac', '-b:a', '160k', '-shortest', '-movflags', '+faststart', salida], stdin=subprocess.PIPE)
    for i in range(n):
        ff.stdin.write(fotograma(i).tobytes())
    ff.stdin.close(); ff.wait(); print('ok', salida, round(TOTAL, 1), 's')

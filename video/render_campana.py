#!/usr/bin/env python3
"""Vídeo de encuestas 29N (versión campaña: evolución, gestos nuevos y más movimiento) (vertical 1080x1920). Todas las cifras salen de datos.json.
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
NOMBRE = {'PP': 'PP', 'PSOE': 'PSOE', 'VOX': 'Vox', 'SUMAR': 'F. Amplio', 'PODEMOS': 'Podemos'}
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
rms = rms / max(np.percentile(rms, 98), 1e-6)
rms_suave = np.convolve(rms, np.ones(3) / 3, 'same')

# subtítulos: frases repartidas por longitud dentro de cada clip
subs = []
for e in escenas:
    for c in e['clips']:
        import re
        frases = [f.strip() for f in re.split(r'(?<=[.?!])\s+', c['texto']) if f.strip()]
        tot = sum(len(f) for f in frases); a = c['ini']
        for f in frases:
            b = a + (c['fin'] - c['ini']) * len(f) / tot; subs.append((a, b, f)); e.setdefault('frases', []).append(a); a = b

# ---------- recursos ----------
logo = Image.open(f'{BASE}/logo.png').convert('RGBA'); logo = logo.resize((int(logo.width * 96 / logo.height), 96), Image.LANCZOS)
ALTO_P = 630
SPR = {}
for k in ('neutral', 'explica', 'sorpresa', 'piensa', 'adios', 'presenta', 'encoge', 'ojo', 'senala', 'pulgar', 'brazos'):
    fr = {v: Image.open(f'{BASE}/papiro/{k}_{v}.png').convert('RGBA') for v in ('cerrada', 'abierta', 'parpadeo')}
    bbs = [f.getbbox() for f in fr.values()]
    bb = (min(b[0] for b in bbs), min(b[1] for b in bbs), max(b[2] for b in bbs), max(b[3] for b in bbs))
    esc = ALTO_P / (fr['cerrada'].getbbox()[3] - fr['cerrada'].getbbox()[1])
    SPR[k] = {v: f.crop(bb).resize((int((bb[2] - bb[0]) * esc), int((bb[3] - bb[1]) * esc)), Image.LANCZOS) for v, f in fr.items()}

def centrado(dr, x, y, s, f, fill):
    w = dr.textlength(s, font=f); dr.text((x - w / 2, y), s, font=f, fill=fill)

def badge(dr, x, y, k, f=f_badge, h=58):
    c = col(k); s = NOMBRE.get(k, k).upper(); w = dr.textlength(s, font=f) + 36
    dr.rounded_rectangle((x, y, x + w, y + h), 12, fill=c); dr.text((x + 18, y + (h - f.size) / 2 - 4), s, font=f, fill=txtcol(c))
    return w

def envolver(dr, s, f, ancho):
    lin, cur = [], ''
    for p in s.split(' '):
        prueba = (cur + ' ' + p).strip()
        if dr.textlength(prueba, font=f) <= ancho: cur = prueba
        else: lin.append(cur); cur = p
    return lin + [cur]

def titulo(dr, s, a):
    dr.text((60, 330), s, font=f_titulo, fill=TINTA + (int(255 * a),) if False else TINTA)


# ---------- escenas ----------
def e_gancho(dr, img, lt, e):
    n = int(round(G['n_encuestas'] * ease(lt / 1.4)))
    centrado(dr, W / 2, 300, str(n), f_gigante, VERDE)
    centrado(dr, W / 2, 720, 'encuestas publicadas', f_titulo, TINTA)
    centrado(dr, W / 2, 800, G['subgancho'], f_sub, TINTA2)
    a = ease((lt - 1.6) / 0.5)
    if a > 0:
        s = 'Arranca la campaña'; w = dr.textlength(s, font=f_medio) + 80
        y = 920 + (1 - a) * 40
        dr.rounded_rectangle((W / 2 - w / 2, y, W / 2 + w / 2, y + 90), 45, fill=VERDE)
        centrado(dr, W / 2, y + 18, s, f_medio, (255, 255, 255))

SERIE = [s for s in DAT['serie'] if s['f'] >= G['desde']]
def e_evolucion(dr, img, lt, e):
    dr.text((60, 330), 'Cómo se han movido', font=f_titulo, fill=TINTA)
    dr.text((60, 410), 'Media de las encuestas (sin el CIS), en %', font=f_fecha, fill=TINTA2)
    x0, x1, y0, y1, vmin, vmax = 130, 790, 500, 1080, 0, 35
    X = lambda i: x0 + (x1 - x0) * i / (len(SERIE) - 1)
    Y = lambda v: y1 - (y1 - y0) * (v - vmin) / (vmax - vmin)
    for v in (0, 10, 20, 30):
        dr.line((x0, Y(v), x1, Y(v)), fill=LINEA, width=2)
        s = str(v); dr.text((x0 - 20 - dr.textlength(s, font=f_fecha), Y(v) - 22), s, font=f_fecha, fill=TINTA2)
    dr.text((x0, y1 + 14), G['etq_ini'], font=f_fecha, fill=TINTA2)
    s = G['etq_fin']; dr.text((x1 - dr.textlength(s, font=f_fecha), y1 + 14), s, font=f_fecha, fill=TINTA2)
    prog = ease(lt / 3.2); n = max(2, int(prog * (len(SERIE) - 1)) + 1)
    for k in ('SUMAR', 'VOX', 'PSOE', 'PP'):
        pts = [(X(i), Y(SERIE[i][k])) for i in range(n)]
        dr.line(pts, fill=col(k), width=10, joint='curve')
        xe, ye = pts[-1]; dr.ellipse((xe - 12, ye - 12, xe + 12, ye + 12), fill=col(k))
        if prog > 0.98:
            s = NOMBRE[k] + ' ' + num(DAT['vote'][k]); dr.text((xe + 22, ye - 26), s, font=f_badge.font_variant(size=38), fill=col(k) if k not in ('SUMAR', 'VOX') else TINTA)
    # ventaja PP-PSOE al principio y al final
    t1, t2 = G['t_gap_ini'], G['t_gap_fin']
    for (t_, i, txt) in ((t1, 0, G['gap_ini']), (t2, len(SERIE) - 1, G['gap_fin'])):
        a = ease((lt - t_) / 0.5)
        if a <= 0 or (i > 0 and prog < 0.98): continue
        xa = X(i) + (40 if i == 0 else -40); ya, yb = Y(SERIE[i]['PP']), Y(SERIE[i]['PSOE'])
        dr.line((xa, ya + 14, xa, yb - 14), fill=TINTA, width=5)
        w = dr.textlength(txt, font=f_badge) + 30; xb = xa + 14 if i == 0 else xa - 14 - w
        dr.rounded_rectangle((xb, (ya + yb) / 2 - 30, xb + w, (ya + yb) / 2 + 30), 14, fill=(255, 255, 255), outline=TINTA, width=3)
        dr.text((xb + 15, (ya + yb) / 2 - 22), txt, font=f_badge, fill=TINTA)

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
    dr.text((60, 410), 'Media de las encuestas que publican escaños', font=f_fecha, fill=TINTA2)
    lleno = int(350 * ease(lt / 2.0)); resalta = lt > G['t_resalta']
    dcha = {'PP', 'VOX', 'UPN'}
    for i, (a, x, y) in enumerate(PTS):
        if i >= lleno: continue
        c = col(DOTS[i])
        if resalta and DOTS[i] not in dcha: c = tuple(int(v * .25 + 236 * .75) for v in c)
        dr.ellipse((x - 10, y - 10, x + 10, y + 10), fill=c)
    dr.line((W / 2, 960 - 450, W / 2, 960 - 140), fill=TINTA, width=4)
    centrado(dr, W / 2, 462, 'mayoría · 176', f_fecha, TINTA)
    if resalta:
        a = ease((lt - G['t_resalta']) / 0.8)
        n = int(round(G['pp_vox_antes'] + (G['pp_vox'] - G['pp_vox_antes']) * a)); centrado(dr, W / 2, 975, str(n), f_grande.font_variant(size=120), VERDE)
        centrado(dr, W / 2, 1115, 'escaños de PP + Vox (con UPN)', f_fecha, TINTA)
        if a >= 1: centrado(dr, W / 2, 1165, 'a mediados de octubre: ' + str(G['pp_vox_antes']), f_fecha, TINTA2)

def tarjeta(dr, x, y, w, h, titulo_, filas, nota, a, morado=False):
    off = (1 - a) * 60
    dr.rounded_rectangle((x, y + off, x + w, y + h + off), 28, fill=(255, 255, 255), outline=MORADO if morado else LINEA, width=4)
    dr.text((x + 34, y + 28 + off), titulo_, font=f_titulo, fill=TINTA)
    yy = y + 110 + off
    for k, v in filas:
        badge(dr, x + 34, yy, k); dr.text((x + 270, yy - 6), num(v) + ' %', font=f_valor, fill=TINTA); yy += 74
    dr.text((x + 34, yy + 8), nota, font=f_fecha, fill=MORADO if morado else VERDE)

def e_discordante(dr, img, lt, e):
    dr.text((60, 330), 'Las que se salen de la tendencia', font=f_titulo.font_variant(size=58), fill=TINTA)
    cl = e['clips']; t_g = (cl[0]['fin'] - e['ini']) * 0.35; t_c = cl[1]['ini'] - e['ini']
    a = ease((lt - t_g) / 0.5)
    if a > 0: tarjeta(dr, 60, 430, 960, 340, G['disc1']['nombre'], G['disc1']['filas'], G['disc1']['nota'], a)
    b = ease((lt - t_c) / 0.5)
    if b > 0: tarjeta(dr, 60, 800, 960, 340, 'CIS', G['cis']['filas'], G['cis']['nota'], b, morado=True)

def barra_bloque(dr, y, etiqueta, valor, color, a=1.0):
    x0, x1, maxv = 60, 1020, 260
    dr.text((x0, y), etiqueta, font=f_medio, fill=TINTA)
    dr.rounded_rectangle((x0, y + 60, x1, y + 130), 20, fill=(236, 230, 214))
    dr.rounded_rectangle((x0, y + 60, x0 + (x1 - x0) * valor / maxv * a, y + 130), 20, fill=color)
    s = str(int(round(valor))); dr.text((x1 - dr.textlength(s, font=f_valor) - 20, y + 64), s, font=f_valor, fill=TINTA)
def e_vuelta(dr, img, lt, e):
    dr.text((60, 330), '¿Moverá algo la campaña?', font=f_titulo, fill=TINTA)
    barra_bloque(dr, 470, 'PP + Vox (con UPN)', G['pp_vox'], col('PP'), ease(lt / 0.9))
    xm = 60 + 960 * 176 / 260
    for yy in range(520, 610, 20): dr.line((xm, yy, xm, yy + 10), fill=TINTA, width=4)
    centrado(dr, xm, 616, 'mayoría 176', f_fecha, TINTA)
    a = ease((lt - 1.4) / 0.6)
    if a > 0:
        dr.rounded_rectangle((60, 720 + (1 - a) * 30, 1020, 880 + (1 - a) * 30), 26, fill=(226, 238, 224))
        centrado(dr, W / 2, 740 + (1 - a) * 30, 'Para perder la mayoría tendrían', f_fecha, TINTA2)
        centrado(dr, W / 2, 790 + (1 - a) * 30, 'que dejarse ' + str(G['pp_vox'] - 175) + ' escaños', f_medio, VERDE)
    c2 = e['clips'][1]['ini'] - e['ini']
    b = ease((lt - c2) / 0.6)
    if b > 0:
        centrado(dr, W / 2, 940 + (1 - b) * 30, 'Desde mediados de octubre:', f_fecha, TINTA2)
        centrado(dr, W / 2, 995 + (1 - b) * 30, str(G['pp_vox_antes']) + ' → ' + str(G['pp_vox']) + ' escaños', f_medio, TINTA)

def e_cierre(dr, img, lt, e):
    centrado(dr, W / 2, 380, 'Faltan', f_titulo, TINTA2)
    centrado(dr, W / 2, 450, str(G['dias']), f_gigante, VERDE)
    centrado(dr, W / 2, 860, 'días para el 29N', f_titulo, TINTA)
    a = ease((lt - 1.0) / 0.6)
    if a > 0:
        dr.rounded_rectangle((120, 960, 960, 1040), 40, fill=(233, 226, 242))
        centrado(dr, W / 2, 978, G['aviso_veda'], f_fecha, MORADO)
    b = ease((lt - G.get('t_url', 4.0)) / 0.6)
    if b > 0:
        centrado(dr, W / 2, 1080, 'Todas las encuestas y el pactómetro', f_fecha, TINTA2)
        s = 'enpapel.es/encuestas-29n'; w = dr.textlength(s, font=f_medio) + 70
        dr.rounded_rectangle((W / 2 - w / 2, 1140, W / 2 + w / 2, 1230), 45, fill=VERDE)
        centrado(dr, W / 2, 1156, s, f_medio, (255, 255, 255))

ESC = {'gancho': e_gancho, 'evolucion': e_evolucion, 'escanos': e_escanos, 'discordante': e_discordante, 'vuelta': e_vuelta, 'cierre': e_cierre}

# ---------- fotograma ----------
CADA = 2.3   # segundos entre cambios de gesto (además del cambio en cada frase)
def pose_en(esc, t):
    poses = esc.get('poses', [esc['pose']]); fr_ini = esc.get('frases', [esc['ini']])
    marcas = []
    for j, a in enumerate(fr_ini):
        b = fr_ini[j + 1] if j + 1 < len(fr_ini) else esc['fin']
        x = a
        while x < b - 0.6: marcas.append(x); x += CADA
    marcas = [m for m in marcas if m <= t] or [esc['ini']]
    return poses[(len(marcas) - 1) % len(poses)], marcas[-1]

def fotograma(i):
    t = i / FPS
    img = Image.new('RGBA', (W, H), CREMA + (255,)); dr = ImageDraw.Draw(img)
    dr.rectangle((0, 0, W, 14), fill=VERDE)
    img.alpha_composite(logo, (60, 60))
    s = '29N'; dr.text((W - 60 - dr.textlength(s, font=f_grande.font_variant(size=110)), 46), s, font=f_grande.font_variant(size=110), fill=VERDE)
    dr.text((60, 190), G['eyebrow'], font=f_eyebrow, fill=TINTA2)
    dr.text((60, 232), G['fecha'], font=f_fecha, fill=TINTA)
    dr.line((60, 296, W - 60, 296), fill=TINTA, width=3)
    esc = next((e for e in escenas if e['ini'] <= t < e['fin']), escenas[-1] if t >= escenas[-1]['ini'] else escenas[0])
    lt = t - esc['ini']
    ESC[esc['tipo']](dr, img, lt, esc)
    # personaje: entra andando, cambia de gesto a menudo, se balancea, "habla" con la voz y sale andando
    pose, t_cambio = pose_en(esc, t)
    r = rms[min(i, len(rms) - 1)]; rs = rms_suave[min(i, len(rms) - 1)]
    abierta = r > 0.32 or (rs > 0.25 and i % 4 < 2)
    ciclo = (t + 0.7) % 3.4; parpadeo = ciclo < 0.12 and not abierta
    spr = SPR[pose]['abierta' if abierta else 'parpadeo' if parpadeo else 'cerrada']
    dt = t - t_cambio; salto = -30 * math.sin(math.pi * dt / 0.32) if 0 <= dt < 0.32 else 0
    sy = 1 + 0.035 * rs; sx = 1 - 0.012 * rs
    if 0 <= dt < 0.32: sy *= 1 + 0.07 * math.sin(math.pi * dt / 0.32); sx *= 1 - 0.05 * math.sin(math.pi * dt / 0.32)
    # entrada y salida caminando
    t_ent, t_sal = 0.9, 0.9
    dx = 0; paso = 0
    if t < t_ent: p = ease(t / t_ent); dx = -420 * (1 - p); paso = abs(math.sin(t * 14)) * 22 * (1 - p)
    if t > TOTAL - t_sal: p = ease((t - (TOTAL - t_sal)) / t_sal); dx = -460 * p; paso = abs(math.sin(t * 14)) * 22 * p
    giro = 2.6 * math.sin(t * 1.9) + 1.2 * math.sin(t * 4.3) * rs
    sp = spr.resize((int(spr.width * sx), int(spr.height * sy)), Image.BILINEAR).rotate(giro, resample=Image.BICUBIC, expand=True)
    bob = 8 * math.sin(t * 3.0) - paso
    img.alpha_composite(sp, (int(230 - sp.width / 2 + dx + 10 * math.sin(t * 0.9)), int(1798 - sp.height + bob + salto)))
    # subtítulo
    sub = next((s for s in subs if s[0] <= t < s[1] + 0.15), None)
    if sub:
        x0, x1 = 470, 1040
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

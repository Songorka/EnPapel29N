"""Corta cada hoja (3 copias: boca cerrada, abierta, ojos cerrados) y las alinea entre sí."""
import glob, os, numpy as np
from PIL import Image
os.makedirs('papiro', exist_ok=True)
for f in sorted(glob.glob('hojas/*.png')):
    nombre = os.path.basename(f)[:-4]
    im = Image.open(f).convert('RGBA'); a = np.array(im)[:, :, 3] > 40
    cols = a.sum(0) > 0
    # tramos de columnas con contenido
    tramos, ini = [], None
    for x, c in enumerate(cols):
        if c and ini is None: ini = x
        if not c and ini is not None:
            if x - ini > 80: tramos.append((ini, x))
            ini = None
    if ini is not None: tramos.append((ini, len(cols)))
    # une tramos muy próximos (p. ej. una mano separada del cuerpo)
    unidos = []
    for t in tramos:
        if unidos and t[0] - unidos[-1][1] < 40: unidos[-1] = (unidos[-1][0], t[1])
        else: unidos.append(t)
    if len(unidos) != 3:
        print('AVISO', nombre, unidos); continue
    copias = []
    for x0, x1 in unidos:
        sub = im.crop((x0, 0, x1, im.height)); bb = sub.getbbox(); copias.append(sub.crop(bb))
    # alinear 2 y 3 con la 1 por correlación de máscaras (±25 px)
    ref = np.array(copias[0])[:, :, 3] > 40
    Hh = max(c.height for c in copias) + 60; Ww = max(c.width for c in copias) + 60
    lienzos = []
    base = Image.new('RGBA', (Ww, Hh)); base.alpha_composite(copias[0], (30, Hh - 30 - copias[0].height)); lienzos.append(base)
    refm = np.array(base)[:, :, 3] > 40
    for c in copias[1:]:
        mejor = None
        x0, y0 = 30 + (copias[0].width - c.width) // 2, Hh - 30 - c.height
        for dx in range(-25, 26, 1):
            for dy in range(-12, 13, 2):
                X, Y = x0 + dx, y0 + dy
                if X < 0 or Y < 0 or X + c.width > Ww or Y + c.height > Hh: continue
                m = np.zeros_like(refm); m[Y:Y + c.height, X:X + c.width] = np.array(c)[:, :, 3] > 40
                s = (m & refm).sum() / (m | refm).sum()
                if mejor is None or s > mejor[0]: mejor = (s, X, Y)
        L = Image.new('RGBA', (Ww, Hh)); L.alpha_composite(c, (mejor[1], mejor[2])); lienzos.append(L)
        print(nombre, 'solape %.3f' % mejor[0])
    for suf, L in zip(('cerrada', 'abierta', 'parpadeo'), lienzos):
        L.save(f'papiro/{nombre}_{suf}.png')

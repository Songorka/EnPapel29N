#!/usr/bin/env python3
"""Imagen de portada (1200x675, JPG) para la Agenda semanal de Enpapel.

Uso: python3 noticias/agenda_imagen.py datos.json salida.jpg

datos.json:
{
  "zona": "Majadahonda" | "Zona Noroeste",
  "fechas": "Del 20 al 22 de noviembre",
  "destacados": [                        # 3 o 4 planes, los más llamativos
    {"dia": "Vie 20", "titulo": "Concierto de ...", "lugar": "Casa de la Cultura · 19:00"}
  ],
  "foto": "ruta/opcional/cartel-oficial.jpg"   # si hay, ocupa la franja derecha
}
"""
import json, os, sys
from PIL import Image, ImageDraw, ImageFont, ImageOps

FUENTES = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'fuentes')
W, H = 1200, 675
FONDO = '#151a2b'; ACENTO = '#f2b84b'; TEXTO = '#ffffff'; SUAVE = '#b9bdd0'
COLOR_ZONA = {'Majadahonda': '#11512a', 'Zona Noroeste': '#4f3f93'}


def f(nombre, tam):
    return ImageFont.truetype(os.path.join(FUENTES, nombre), tam)


def recorta(dr, texto, fuente, ancho):
    if dr.textlength(texto, font=fuente) <= ancho:
        return texto
    while texto and dr.textlength(texto + '…', font=fuente) > ancho:
        texto = texto[:-1]
    return texto.rstrip() + '…'


def generar(d, salida):
    im = Image.new('RGB', (W, H), FONDO)
    dr = ImageDraw.Draw(im)
    ancho_txt = W - 112
    if d.get('foto') and os.path.exists(d['foto']):
        franja = 430
        foto = ImageOps.fit(Image.open(d['foto']).convert('RGB'), (franja, H), Image.LANCZOS, centering=(0.5, 0.3))
        im.paste(foto, (W - franja, 0))
        ancho_txt = W - franja - 112
    color = COLOR_ZONA.get(d.get('zona'), '#4f3f93')
    dr.rectangle((0, 0, 14, H), fill=ACENTO)
    x = 56
    dr.text((x, 52), 'AGENDA', font=f('InterDisplay-Black.otf', 30), fill=ACENTO)
    zona = d.get('zona', '')
    tz = f('Inter-Bold.otf', 24)
    wz = dr.textlength(zona.upper(), font=tz)
    x2 = x + dr.textlength('AGENDA', font=f('InterDisplay-Black.otf', 30)) + 18
    dr.rounded_rectangle((x2, 50, x2 + wz + 28, 90), radius=8, fill=color)
    dr.text((x2 + 14, 70), zona.upper(), font=tz, fill=TEXTO, anchor='lm')
    tit = f('InterDisplay-ExtraBold.otf', 56)
    dr.text((x, 112), recorta(dr, 'Planes del fin de semana', tit, ancho_txt), font=tit, fill=TEXTO)
    dr.text((x, 186), d.get('fechas', ''), font=f('Inter-SemiBold.otf', 30), fill=SUAVE)
    y = 262
    dest = d.get('destacados', [])[:4]
    alto = (H - y - 70) // max(len(dest), 1)
    for p in dest:
        dr.rounded_rectangle((x, y + 6, x + 110, y + 48), radius=8, outline=ACENTO, width=2)
        dr.text((x + 55, y + 27), recorta(dr, p.get('dia', ''), f('Inter-Bold.otf', 22), 100), font=f('Inter-Bold.otf', 22), fill=ACENTO, anchor='mm')
        ft = f('Inter-Bold.otf', 28)
        dr.text((x + 130, y + 2), recorta(dr, p.get('titulo', ''), ft, ancho_txt - 130), font=ft, fill=TEXTO)
        fl = f('Inter-Medium.otf', 21)
        dr.text((x + 130, y + 38), recorta(dr, p.get('lugar', ''), fl, ancho_txt - 130), font=fl, fill=SUAVE)
        y += alto
    dr.text((x, H - 40), 'enpapel.es', font=f('Inter-Bold.otf', 22), fill=ACENTO, anchor='lm')
    im.save(salida, quality=88)


if __name__ == '__main__':
    if len(sys.argv) != 3:
        sys.exit(__doc__)
    generar(json.load(open(sys.argv[1], encoding='utf-8')), sys.argv[2])
    print('Imagen creada:', sys.argv[2])

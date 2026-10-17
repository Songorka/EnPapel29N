# Personaje de los vídeos de encuestas (ficha oficial)

Imagen de referencia: `ficha-oficial.png` (Higgsfield, job c4a5fb24-3f2a-4a39-83b5-fde02a233cac).
Usarla SIEMPRE como referencia al generar al personaje. No cambiar nada sin el visto bueno de Gorka.

## Rasgos fijos
- Cuerpo y cabeza: un periódico doblado color crema (#f7f3e8), con varias hojas visibles en el borde superior.
- Portada: franja verde oscuro arriba (cabecera), líneas grises de texto (nunca letras legibles) y un recuadro morado (#4f3f93) a la derecha del torso.
- Cara: gafas redondas finas negras, ojos ovalados oscuros con un brillo blanco, cejas oscuras expresivas, sonrisa tranquila.
- Bufanda de punto verde oscuro (#11512a) con flecos, un extremo colgando por delante.
- Brazos y piernas finos verde oscuro, manos de cuatro dedos tipo guante.
- Zapatillas de lona verde oscuro con suela y cordones crema.
- Estilo: ilustración vectorial 2D plana, contorno gris oscuro uniforme, sombra suave de un tono. Tono sobrio, adulto, nada infantil.

## Uso en los vídeos
- Los datos van en gráficos generados desde index.html (nunca cifras dibujadas por la IA).
- El personaje aparece en la entrada, en la despedida y pequeño en una esquina durante los gráficos.
- Aviso visible: "Personaje animado con IA".
- Nunca se publica del 24 al 29 de noviembre (veda).

## Nombre
- Se llama **Papiro**.

## Voz (elegida por Gorka el 17/10/2026, sustituye a "Dylan")
- Higgsfield, modelo `seed_audio`, formato wav 44,1 kHz, `speech_rate: 8`.
- Voz clonada de la muestra aprobada: `medias: [{value: "71364d71-1ba7-4d82-8883-25c0c3ce24b2", role: "audio_references"}]`
  (esa muestra se creó con la ficha del personaje como referencia de imagen, pitch +2, velocidad +8).
- Generar frases cortas (máx. ~130 caracteres por clip): con textos largos el motor a veces corta el final.

## Animación
- `video/papiro/<gesto>_{cerrada,abierta,parpadeo}.png`: 8 gestos (neutral, explica, presenta, ojo, encoge, piensa, sorpresa, adios),
  cada uno con boca cerrada, boca abierta y parpadeo, alineados entre sí (`video/cortar.py`).
- `video/render.py`: la boca se abre con la voz, parpadea cada ~3,4 s y cambia de gesto en cada frase (con un saltito).

# Noticia diaria de encuestas 29N · instrucciones de redacción

Se publica **una sola noticia al día**, y solo si ese día hay encuestas nuevas. Nunca durante la veda (24–29 nov).
Autor: Redacción. Tono: periodístico pero llano, como se lo contarías a un vecino informado; frases cortas, sin tecnicismos de demoscopia («horquilla», «estimación», «submuestra»…) o explicados al momento; neutral entre partidos, con algo de chispa en el segundo párrafo. Texto siempre original: nunca se copian frases de las fuentes.

## Nombres de partidos
El antiguo espacio de Sumar se llama **Frente Amplio** (candidata: Ada Colau; incluye Movimiento Sumar, IU, Más Madrid y Comuns). Nunca escribas «Sumar» para la candidatura de 2026: solo para hablar del resultado de 2023 («Sumar, hoy Frente Amplio»). Podemos va aparte (salvo en Canarias y la Comunidad Valenciana). En los datos se sigue usando la clave interna SUMAR.

## Titular
Corto (máx. ~80 caracteres), con el dato principal de la encuesta nueva y los días que faltan cuando aporte. Al hablar de distancias, que quede claro quién va delante: «X queda a N puntos de Y» significa que X va detrás (bien: «deja al PSOE a 2,6 puntos del PP» si el PP va primero). Relee el titular comprobándolo con las cifras. Ejemplo: «40dB mantiene la mayoría de PP y Vox a 50 días del 29N».

## Párrafo 1 · Qué trae la encuesta nueva
- El dato principal: estimación de PP, PSOE, Vox, Frente Amplio y Podemos, y escaños si los publica.
- **Datos obligatorios por ley** (art. 69 LOREG): quién la ha hecho, quién la ha encargado y la ficha técnica (fechas del trabajo de campo, tamaño de la muestra, método y margen de error). Lo que la fuente no publique se dice como «no publicado». Si el margen de error no viene publicado y hay muestra, se puede dar el teórico, avisando de que es teórico (95 %, p=q=0,5).
- **¿Es previsible o sorprende?** Compararla con la anterior de la misma encuestadora y con la media de las demás. Si se aleja más de 2 puntos de la media en algún partido grande, se dice que es una encuesta que se sale de lo esperado. Si no, se dice que confirma la tendencia.
- Si ese día hay varias encuestas nuevas, el párrafo abre con la más relevante y menciona brevemente las demás.

## Párrafo 2 · La tendencia general (con algo de chispa)
- La media del panel, cómo se ha movido desde el día 5 de octubre y quién sube o baja comparando cada encuestadora consigo misma.
- La comparación con el 23J cuando dé titular (en 2023 Podemos fue dentro de Sumar: para comparar se suman Frente Amplio y Podemos).
- La confianza: si las encuestas coinciden mucho o poco entre sí.
- Se permite una imagen o una comparación con gracia, siempre sin tomar partido.

## Párrafo 3 · Días que faltan y escenarios
- Cuántos días quedan hasta el 29N.
- Los escenarios posibles con la media de escaños (mayoría: 176): PP + Vox; PP con otros apoyos; bloque de investidura (PSOE, Frente Amplio, Podemos, ERC, Junts, Bildu, PNV, BNG, CC); y otras sumas solo si son aritméticamente posibles.
- Qué tendría que pasar para que cambie cada escenario: cuántos escaños le faltan o le sobran a cada bloque.

## Cierre
- Enlace a la página: «Todas las encuestas, la media y el pactómetro, en enpapel.es/encuestas-29n».
- Línea de **Ficha técnica** completa con cada encuesta citada: encuestadora, medio, fechas de campo, muestra, método, margen de error y enlace a la fuente original.

## Estructura en WordPress
- Un subtítulo H2 antes de cada bloque: «Qué dice la encuesta de <encuestadora>», uno con gancho para la tendencia y «A N días del 29N: los escenarios».
- La línea en cursiva del método/muestra va en su propio párrafo (ningún párrafo de más de 150 palabras).
- Categorías: Elecciones 29N (id 7041, **categoría principal**) + Slider (id 58). Autor: En Papel (id 4).
- Extracto: una o dos frases con el dato principal.

## SEO (Yoast)
- Frase clave: «encuesta <encuestadora>» (p. ej. «encuesta 40dB»). Debe aparecer en el título SEO, la URL, el primer subtítulo y al menos dos veces en el texto.
- URL corta: encuesta-<encuestadora>-<idea-clave>-29n (p. ej. encuesta-40db-pp-vox-mayoria-29n).
- Título SEO (≤ 60 caracteres antes de « - sitio»): «Encuesta <encuestadora>: <dato clave> …» + %%sep%% %%sitename%%.
- Meta descripción (120–155 caracteres) con las cifras de los tres primeros partidos.
- Título y descripción para Facebook/X propios (más directos, con cifras).
- Tipo de artículo de schema: NewsArticle.
- Etiquetas (reutilizar las existentes, no crear duplicados): elecciones (1418), elecciones generales (7042), encuestas electorales (7043), 29N (7044) + la de la encuestadora (crear si no existe, p. ej. 40dB = 7045) + los partidos que salgan en el titular o el primer párrafo: PP (1786), psoe (174), vox (2207), Frente Amplio (crear si no existe; ya no se usa «Sumar»), Podemos (1826). Entre 6 y 10 etiquetas.
- Texto alternativo de la imagen: el campo `alt` del generador. Nombre del archivo: encuesta-<encuestadora>-29n-<día>-<mes>.png.
- Enlace interno a enpapel.es/encuestas-29n y enlace externo a la fuente original.
- Tras publicar: vaciar la caché de WP Super Cache para que salga en la portada.

## Imagen destacada
`python3 noticias/imagen.py --salida imagen.png` crea la imagen del día (sin repetir). Su texto alternativo es el campo `alt` que imprime el programa.

## Enlace a la página de encuestas (obligatorio)
- Toda noticia lleva un botón verde bien visible «📊 Ver todas las encuestas, la media y el pactómetro» tras el primer bloque (lo pone preparar.py) y además la línea final con el enlace a enpapel.es/encuestas-29n.
- En el texto, al hablar de la media o del pactómetro, se puede enlazar también a https://enpapel.es/encuestas-29n/.

## Post para X (campo `post_x` del borrador)
- Máx. ~230 caracteres, sin enlace (se añade solo, con #29N y #Encuestas si no están).
- Tono: que llame la atención pero sin caer en el sensacionalismo ni en el periodismo basura. Un titular con gancho, como el de una buena portada: verbo fuerte y el dato más llamativo del día por delante.
- Un solo emoji al principio, sobrio (📊, 📈, 📉, 🗳️). Nada de MAYÚSCULAS, signos de exclamación, 🚨/😱/🔥 ni preguntas retóricas dirigidas a un líder o partido.
- Estructura: dato o idea que engancha + cifras clave + cierre que invite a leer (p. ej. «Así queda el reparto a 50 días del #29N 👇»). Varía el ángulo cada día (quién sube, quién baja, el reparto de escaños, la sorpresa de la encuesta, lo que dice la media).
- Todo debe salir de los datos (nada exagerado: «se desploma» solo si baja más de 2 puntos, «sorpresa» solo si se aparta más de 2 puntos de la media…). Neutral: el foco cae sobre el partido que toque según los números.
- Ejemplos:
  «📊 PP y Vox superarían los 200 escaños, según la última encuesta de 40dB. El PSOE recorta algo, pero sigue lejos. Así queda el reparto a 50 días del #29N 👇»
  «📈 Vox gana más de seis puntos desde el 23J y es el partido en el que más coinciden las encuestas. La nueva de IMOP lo sitúa en el 19 %. #29N»
  «🗳️ La encuesta de hoy se sale de la media: Sigma Dos deja al PSOE a solo dos puntos del PP. ¿Cambio de tendencia o dato aislado? Lo analizamos #29N»
- Se publica en @EnPapel2021 justo después de la noticia, con la misma imagen.

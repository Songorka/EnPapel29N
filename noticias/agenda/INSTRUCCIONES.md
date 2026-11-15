# Agenda semanal de Enpapel

Cada **jueves por la tarde** se preparan dos noticias con los planes del fin de semana (viernes a domingo):

1. **Agenda de Majadahonda**, ordenada por días.
2. **Agenda de la Zona Noroeste**, ordenada por municipio: Las Rozas, Pozuelo de Alarcón, Boadilla del Monte,
   Villanueva de la Cañada, Villanueva del Pardillo, Torrelodones y Galapagar.

Se dejan como **borrador**. A Gorka le llega un correo con el resumen completo (no puede ver los borradores desde
el móvil) y él da el OK en un chat. Nada se publica ni sale en X sin su OK.

## Fuentes (solo oficiales)

- Webs de cada ayuntamiento: agenda, notas de prensa (muchos publican el jueves una nota tipo «agenda del fin de
  semana»), concejalías de cultura, deportes, juventud y mayores.
- Portales municipales de turismo y cultura (p. ej. visitlasrozas.es), teatros y auditorios municipales.
- Webs de los organizadores del evento (para precios y entradas) y carteles oficiales.
- **Nunca otros periódicos** como fuente. Pueden servir para descubrir un evento, pero el dato se confirma en la
  fuente oficial; si no se puede confirmar, el evento no entra.
- Localiza las páginas con WebSearch y ábrelas con WebFetch (no construyas URLs a mano).

## Qué entra y qué no

- Entran: cultura, música, teatro, cine, ferias, gastronomía, deporte popular, infantil y familiar, mayores,
  fiestas, mercadillos, talleres abiertos y exposiciones que se puedan visitar ese fin de semana.
- No entran: actos de partidos, mítines o actos de campaña (y del 24 al 29 de noviembre de 2026, nada electoral),
  plenos, cursos con plazo cerrado, cosas ya pasadas o sin fecha confirmada.
- Ningún dato inventado ni estimado: si falta la hora o el precio, se dice «consultar en ...» con el enlace.
- Entre 8 y 15 planes por noticia (menos si de verdad no hay más). Lo más llamativo, primero.

## Formato de cada noticia

- Titular con gancho y el nombre del municipio o «Zona Noroeste» y las fechas, p. ej.
  «Teatro, mercado navideño y cross popular: la agenda de Majadahonda para el fin de semana del 20 al 22 de noviembre».
- Entradilla de 2-3 líneas con lo más destacado.
- Majadahonda: un `<h2>` por día (Viernes 20, Sábado 21, Domingo 22) y debajo cada plan.
  Zona Noroeste: un `<h2>` por municipio (solo los que tengan planes).
- Cada plan: **nombre en negrita**, qué es en una frase, día y hora, lugar (con dirección si ayuda), precio
  («gratis» si lo es; «entrada libre hasta completar aforo» si lo dice) y enlace oficial para más información o
  entradas (`target="_blank" rel="noopener"`).
- Si hay un plan que dura todo el fin de semana (ruta de la tapa, feria...), va arriba en un bloque «Todo el fin de semana».
- Cierre: línea en cursiva con las fuentes («Fuentes: Ayuntamiento de ..., ...»).
- Categorías: `["Agenda", 45, 58]` en Majadahonda y `["Agenda", 50, 58]` en Zona Noroeste
  (la categoría «Agenda» se crea sola la primera vez). `seo.categoria_principal`: `"Agenda"`. Autor 4.
- Etiquetas: «agenda», «fin de semana», «planes», el municipio o municipios y 2-4 temas.
- SEO: frase clave tipo «agenda Majadahonda fin de semana» / «planes fin de semana zona noroeste Madrid»;
  título SEO ≤ 60 caracteres; descripción ≤ 155.
- `x_texto`: 3-4 planes con emoji y «Toda la agenda 👇», máx. 230 caracteres, sin enlace.

## Imagen

- Portada: `python3 noticias/agenda_imagen.py datos.json noticias/imagenes/agenda/<fecha>-<zona>.jpg`
  (ver el formato de datos dentro del script; 3-4 destacados). Si consigues descargar el cartel oficial de un
  evento (curl a la web del ayuntamiento a veces funciona), pásalo como `"foto"`; si no, sin foto.
- Fotos dentro del texto (opcional): carteles oficiales descargados, como JPG, con `fotos_cuerpo` y `{{FOTO_n}}`,
  alt descriptivo y pie con la fuente.

## Ficheros

- Cola (borrador): `noticias/cola/<fecha>-agenda-majadahonda.json` y `noticias/cola/<fecha>-agenda-noroeste.json`
  con `"estado": "draft"`, donde `<fecha>` es la del jueves (AAAA-MM-DD). El campo `"fecha"` igual que el nombre.
- Pendiente de OK: `noticias/agenda/<fecha>-pendiente.json` con, para cada noticia: `fecha`, `titulo`, `id` del
  borrador, `x_texto`, `imagen` e `imagen_alt`. Sirve para publicarlas después.

## Cuando Gorka da el OK («publica la agenda», «ok agenda»...)

Para cada noticia de `noticias/agenda/<fecha>-pendiente.json` que él apruebe:

1. `noticias/cola/<fecha>-agenda-<zona>-publicar.json` → `{"fecha": "<fecha>-agenda-<zona>-publicar", "corregir_id": <id>, "estado": "publish"}`.
   Push y esperar a `noticias/publicadas/<fecha>-agenda-<zona>-publicar.json` (trae el `enlace`).
2. `noticias/cola/<fecha>-agenda-<zona>-x.json` → `{"fecha": "<fecha>-agenda-<zona>", "solo_x": true, "enlace": "<enlace>",
   "x_texto": ..., "x_etiquetas": [], "x_campana": "agenda", "imagen": ..., "imagen_alt": ...}`. Push y esperar a
   `noticias/publicadas/<fecha>-agenda-<zona>-x.json` (trae `x_enlace`).
3. Un fichero de cola por push, esperando a que la Action vacíe la cola antes del siguiente
   (`mkdir -p noticias/cola` antes de escribir: la carpeta desaparece cuando se vacía).
4. Pasar a Gorka los enlaces de la noticia y del post de X.

Si pide cambios, corregirlos en el borrador con `corregir_id` (contenido, titulo, extracto...) antes de publicar.

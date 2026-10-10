# EnPapel29N

Seguimiento de las encuestas de las elecciones generales del 29 de noviembre de 2026 para [Enpapel](https://enpapel.es).

- `index.html` es el dashboard completo. Los datos están en el bloque `<script type="application/json" id="datos">`.
- Una tarea programada revisa cada mañana si hay encuestas nuevas, actualiza ese bloque y hace commit aquí.
- Del 24 al 29 de noviembre (veda electoral) la página oculta las cifras.

Publicado con GitHub Pages en https://songorka.github.io/enpapel29n/

## Noticia diaria en Enpapel

- `noticias/plantilla.md`: reglas de redacción y SEO. `noticias/ejemplo-borrador.json`: ejemplo.
- `noticias/imagen.py`: imagen destacada del día (7 tipos que rotan; nunca repite una imagen).
- `noticias/preparar.py`: convierte el borrador en `noticias/cola/<fecha>.json`.
- `.github/workflows/publicar-noticia.yml` + `noticias/publicar.py`: al subir algo a `noticias/cola/`, GitHub lo publica en WordPress con los secretos `WP_USER` y `WP_APP_PASSWORD` y deja el enlace en `noticias/publicadas/<fecha>.json`.

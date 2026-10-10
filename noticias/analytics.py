#!/usr/bin/env python3
"""Saca de Google Analytics 4 los datos del día anterior para el informe diario (centrado en el 29N).

Lo ejecuta GitHub Actions cada mañana (.github/workflows/analytics-diario.yml) con los secretos:
  GA_CREDENTIALS   contenido completo del JSON de la cuenta de servicio (solo lectura en Analytics)
  GA_PROPERTY_ID   número de la propiedad de GA4
Deja el resultado en analytics/<fecha de ayer>.json para que la tarea de las 7:46 lo resuma en el email.
"""
import json, os, sys, time
from datetime import date, datetime, timedelta, timezone

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SALIDA = os.path.join(RAIZ, 'analytics')


def cliente():
    from google.oauth2 import service_account
    from google.analytics.data_v1beta import BetaAnalyticsDataClient
    info = json.loads(os.environ['GA_CREDENTIALS'])
    cred = service_account.Credentials.from_service_account_info(
        info, scopes=['https://www.googleapis.com/auth/analytics.readonly'])
    return BetaAnalyticsDataClient(credentials=cred)


def main():
    from google.analytics.data_v1beta.types import (RunReportRequest, DateRange, Dimension, Metric, OrderBy,
                                                    FilterExpression, FilterExpressionList, Filter)
    prop = 'properties/' + os.environ['GA_PROPERTY_ID'].strip()
    c = cliente()
    hoy = datetime.now(timezone(timedelta(hours=2))).date()  # aproximación a Madrid; el informe es de "ayer"
    ayer = hoy - timedelta(days=1)
    hace7 = ayer - timedelta(days=7)
    iso = lambda d: d.isoformat()

    def f_contiene(campo, valor):
        return FilterExpression(filter=Filter(field_name=campo, string_filter=Filter.StringFilter(
            match_type=Filter.StringFilter.MatchType.CONTAINS, value=valor)))

    F_29N = FilterExpression(or_group=FilterExpressionList(expressions=[
        f_contiene('pagePath', '/encuestas-29n'), f_contiene('pagePath', '/elecciones-29n/')]))

    def informe(dims, mets, desde, hasta, filtro=None, orden=None, limite=10):
        r = c.run_report(RunReportRequest(
            property=prop, dimensions=[Dimension(name=d) for d in dims], metrics=[Metric(name=m) for m in mets],
            date_ranges=[DateRange(start_date=iso(desde), end_date=iso(hasta))],
            dimension_filter=filtro,
            order_bys=[OrderBy(metric=OrderBy.MetricOrderBy(metric_name=orden), desc=True)] if orden else None,
            limit=limite))
        filas = []
        for row in r.rows:
            d = {dims[i]: v.value for i, v in enumerate(row.dimension_values)}
            d.update({mets[i]: float(v.value) for i, v in enumerate(row.metric_values)})
            filas.append(d)
        return filas

    def total(mets, desde, hasta, filtro=None):
        f = informe([], mets, desde, hasta, filtro, limite=1)
        return {m: int(f[0][m]) if f else 0 for m in mets}

    M = ['activeUsers', 'sessions', 'screenPageViews']
    datos = {
        'fecha': iso(ayer), 'generado': datetime.now(timezone.utc).isoformat(timespec='minutes'),
        'web': {'ayer': total(M, ayer, ayer), 'mismo_dia_semana_pasada': total(M, hace7, hace7),
                'media_7_dias': {k: round(v / 7) for k, v in total(M, ayer - timedelta(days=6), ayer).items()}},
        '29n': {
            'ayer': total(['activeUsers', 'screenPageViews'], ayer, ayer, F_29N),
            'mismo_dia_semana_pasada': total(['activeUsers', 'screenPageViews'], hace7, hace7, F_29N),
            'pagina_encuestas': total(['activeUsers', 'screenPageViews'], ayer, ayer, f_contiene('pagePath', '/encuestas-29n')),
            'noticias': informe(['pageTitle', 'pagePath'], ['screenPageViews', 'activeUsers'], ayer, ayer,
                                f_contiene('pagePath', '/elecciones-29n/'), 'screenPageViews', 5),
            'fuentes': informe(['sessionSource'], ['activeUsers'], ayer, ayer, F_29N, 'activeUsers', 6),
            'acumulado_desde_5_oct': total(['activeUsers', 'screenPageViews'], date(2026, 10, 5), ayer, F_29N),
        },
        'mas_leidas': informe(['pageTitle', 'pagePath'], ['screenPageViews'], ayer, ayer, None, 'screenPageViews', 6),
        'fuentes_web': informe(['sessionDefaultChannelGroup'], ['sessions'], ayer, ayer, None, 'sessions', 6),
        'dispositivos': informe(['deviceCategory'], ['activeUsers'], ayer, ayer, None, 'activeUsers', 3),
        'desde_x': total(['sessions', 'activeUsers'], ayer, ayer, FilterExpression(or_group=FilterExpressionList(expressions=[
            f_contiene('sessionSource', 't.co'), f_contiene('sessionSource', 'x.com'), f_contiene('sessionSource', 'twitter')]))),
    }
    os.makedirs(SALIDA, exist_ok=True)
    ruta = os.path.join(SALIDA, f'{iso(ayer)}.json')
    json.dump(datos, open(ruta, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    print(json.dumps(datos['web']['ayer']), json.dumps(datos['29n']['ayer']))


if __name__ == '__main__':
    try:
        main()
    except Exception as e:
        os.makedirs(SALIDA, exist_ok=True)
        with open(os.path.join(SALIDA, 'ultimo-error.txt'), 'w', encoding='utf-8') as f:
            f.write(time.strftime('%Y-%m-%d %H:%M UTC', time.gmtime()) + '\n' + f'{type(e).__name__}: {str(e)[:800]}\n')
        print('ERROR:', type(e).__name__, str(e)[:800], file=sys.stderr)
        sys.exit(1)

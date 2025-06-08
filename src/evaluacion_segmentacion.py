"""
Este módulo evalúa la segmentación de párrafos en la base de datos,
calculando el número de fragmentos y la longitud media por estrategia
de segmentación para textos en español.
"""

import pandas as pd
from db_utils import connect_to_db

# Conexión a la base de datos usando db_utils
conn = connect_to_db()
if conn is None:
    raise RuntimeError("No se pudo conectar a la base de datos.")

# Consulta para obtener número de fragmentos y longitud media por estrategia (solo idioma español)
QUERY = """
SELECT estrategia_segmentacion,
       COUNT(*) AS total_fragmentos,
       ROUND(AVG(LENGTH(texto)), 2) AS longitud_media
FROM Parrafos
WHERE idioma = 'es'
GROUP BY estrategia_segmentacion
ORDER BY estrategia_segmentacion;
"""

# Ejecutar la consulta y cargar resultados
df_resultados = pd.read_sql_query(QUERY, conn)

# Mostrar resultados
print("\nResumen por estrategia de segmentación (idioma: español):")
print(df_resultados)

# Guardar como CSV opcionalmente
df_resultados.to_csv("validacion_segmentacion_5_3.csv", index=False)

# Cierre de conexión
conn.close()

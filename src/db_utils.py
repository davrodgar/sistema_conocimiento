"""
Módulo db_utils.py
-------------------
Este módulo contiene funciones comunes para interactuar con la base de datos 
SQLite utilizada en el sistema.
También incluye la documentación de la estructura de la tabla `Ficheros`.

Tabla `Ficheros`:
------------------
- `Id` (INTEGER, PRIMARY KEY): Identificador único del registro.
- `nombreOriginal` (TEXT): Nombre original del archivo procesado.
- `tipoOriginal` (TEXT): Extensión del archivo original (por ejemplo, `.pdf`, `.docx`).
- `metodoExtraccion` (TEXT): Método utilizado para procesar el archivo 
(por ejemplo, `PDFPlumber`, `TIKA_text_plain`).
- `ficheroGenerado` (TEXT): Nombre del archivo generado tras el procesamiento.
- `tipoExtraccion` (TEXT): Tipo de extracción o formato del archivo generado 
(por ejemplo, `.txt`, `.json`).
- `tiempoExtraccion` (INTEGER): Tiempo que tomó el procesamiento en segundos.
- `observaciones` (TEXT, opcional): Información adicional sobre el procesamiento.
- `fechaExtraccion` (INTEGER): Marca de tiempo (timestamp) del momento de extracción.
"""

import os
import sqlite3
import json
from datetime import datetime

# Ruta a la base de datos SQLite
BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
DB_PATH = os.path.join(BASE_DIR, "data", "sistema_conocimiento.db")
# Ruta a la base de datos SQLite
print(f"[INFO] Ruta a la base de datos SQLite: {DB_PATH}")


def connect_to_db():
    """
    Establece una conexión con la base de datos SQLite.

    :return: Objeto de conexión a la base de datos si existe, de lo contrario None.
    """
    if not os.path.exists(DB_PATH):
        print(f"❌ No se encontró la base de datos en: {DB_PATH}")
        return None
    return sqlite3.connect(DB_PATH)


def check_existing_fichero(nombre_original, tipo_original, metodo_extraccion):
    """
    Comprueba si ya existe un fichero con el mismo nombre, tipo original y método de extracción.

    :param nombre_original: Nombre original del archivo.
    :param tipo_original: Extensión del archivo original.
    :param metodo_extraccion: Método de extracción utilizado.
    :return: El ID del registro existente si se encuentra, de lo contrario None.
    """
    conn = connect_to_db()
    if not conn:
        return None

    cursor = conn.cursor()
    try:
        query = """
           SELECT Id FROM Ficheros
           WHERE nombreOriginal = ? AND tipoOriginal = ? AND metodoExtraccion = ?
        """
        params = (nombre_original, tipo_original, metodo_extraccion)
        cursor.execute(query, params)
        result = cursor.fetchone()
        return result[0] if result else None
    except sqlite3.Error as e:
        print(f"❌ Error al comprobar el registro en la base de datos: {e}")
        return None
    finally:
        conn.close()


def add_fichero_record(nombre_original, tipo_original, metodo_extraccion,
                       fichero_generado, tipo_extraccion,
                       tiempo_extraccion, observaciones=None):
    """
    Añade un registro a la tabla Ficheros de la base de datos.

    :param nombre_original: Nombre original del archivo.
    :param tipo_original: Extensión del archivo original.
    :param metodo_extraccion: Método de extracción utilizado.
    :param fichero_generado: Ruta del fichero generado tras la extracción.
    :param tipo_extraccion: Tipo de extracción (formato solicitado).
    :param tiempo_extraccion: Tiempo que tomó la extracción en segundos.
    :param observaciones: Observaciones adicionales (opcional).
    """
    conn = connect_to_db()
    if not conn:
        return

    cursor = conn.cursor()
    try:
        fichero_generado_nombre = os.path.basename(fichero_generado)
        fecha_extraccion = int(datetime.now().timestamp())
        cursor.execute("""
            INSERT INTO Ficheros (
                nombreOriginal, tipoOriginal, metodoExtraccion, ficheroGenerado, 
                tipoExtraccion, tiempoExtraccion, observaciones, fechaExtraccion
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            nombre_original, tipo_original, metodo_extraccion, fichero_generado_nombre,
            tipo_extraccion, tiempo_extraccion, observaciones, fecha_extraccion
        ))
        conn.commit()
        print(f"✅ Registro añadido a la base de datos para el archivo: {nombre_original}")
    except sqlite3.Error as e:
        print(f"❌ Error al añadir el registro a la base de datos: {e}")
    finally:
        conn.close()


def obtener_metodo_tipo_extraccion(nombre_archivo):
    """
    Obtiene los valores de los campos Id, metodoExtraccion, tipoExtraccion, tipoOriginal
    y nombreOriginal
    de la tabla Ficheros para un archivo específico.

    :param nombre_archivo: Nombre del archivo a buscar en la tabla Ficheros.
    :return: Diccionario con Id, metodoExtraccion, tipoExtraccion, tipoOriginal
    y nombreOriginal, o None si no se encuentra.
    """
    conn = connect_to_db()
    if not conn:
        return None

    cursor = conn.cursor()
    try:
        query = """
            SELECT Id, metodoExtraccion, tipoExtraccion, tipoOriginal, nombreOriginal
            FROM Ficheros
            WHERE ficheroGenerado = ?
        """
        print(f"[INFO] Ejecutando consulta: {query} con parámetro: {nombre_archivo}")
        cursor.execute(query, (nombre_archivo,))
        resultado = cursor.fetchone()
        if resultado:
            return {
                "id_fichero": resultado[0],
                "metodo_extraccion": resultado[1],
                "tipo_extraccion": resultado[2],
                "tipo_original": resultado[3],
                "nombre_original": resultado[4]  # Nuevo campo añadido
            }
        return None
    except sqlite3.Error as e:
        print(f"❌ Error al obtener los datos de extracción: {e}")
        return None
    finally:
        conn.close()

def insertar_parrafo_segmentado(id_fichero, id_parrafo, texto, longitud, idioma,
                                 titulos, estrategia, metodo, tipo_extraccion):
    """
    Inserta un nuevo párrafo segmentado en la tabla Parrafos de la base de datos.

    :param id_fichero: ID del fichero asociado.
    :param id_parrafo: ID del párrafo.
    :param texto: Texto del párrafo.
    :param longitud: Longitud del texto.
    :param idioma: Idioma del párrafo.
    :param titulos: Lista de títulos asociados al párrafo.
    :param estrategia: Estrategia de segmentación utilizada.
    :param metodo: Método de extracción utilizado.
    :param tipo_extraccion: Tipo de extracción.
    """
    conn = None
    try:
        conn = sqlite3.connect(DB_PATH)
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO Parrafos (
                id_fichero, id_parrafo, texto, longitud, idioma,
                titulos, estrategia_segmentacion, metodo_extraccion,
                tipo_extraccion, modelo_embedding, embedding
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, NULL, NULL)
        """, (
            id_fichero, id_parrafo, texto, longitud, idioma,
            json.dumps(titulos, ensure_ascii=False), estrategia, metodo, tipo_extraccion
        ))
        conn.commit()
        print(f"✅ Párrafo insertado correctamente (ID párrafo: {id_parrafo})")
    except sqlite3.Error as e:
        print(f"❌ Error al insertar el párrafo en la base de datos: {e}")
    finally:
        if conn:
            conn.close()

def obtener_parrafos_sin_embedding():
    """
    Devuelve una lista de diccionarios con los párrafos cuyo modelo_embedding es NULL.
    Cada diccionario contiene al menos 'id' y 'texto'.
    """
    conn = connect_to_db()
    if not conn:
        return []
    cursor = conn.cursor()
    try:
        query = """
            SELECT id, texto FROM Parrafos
            WHERE modelo_embedding IS NULL OR modelo_embedding = ''
        """
        cursor.execute(query)
        resultados = cursor.fetchall()
        return [{"id": row[0], "texto": row[1]} for row in resultados]
    except sqlite3.Error as e:
        print(f"❌ Error al obtener párrafos sin embedding: {e}")
        return []
    finally:
        conn.close()

def actualizar_embedding_parrafo(id_parrafo, embedding, modelo):
    """
    Actualiza el embedding y el modelo_embedding de un párrafo dado su id.
    :param id_parrafo: ID del párrafo a actualizar.
    :param embedding: Embedding serializado como JSON (lista de floats).
    :param modelo: Nombre del modelo utilizado.
    """
    conn = connect_to_db()
    if not conn:
        return
    cursor = conn.cursor()
    try:
        query = """
            UPDATE Parrafos
            SET embedding = ?, modelo_embedding = ?
            WHERE id = ?
        """
        cursor.execute(query, (embedding, modelo, id_parrafo))
        conn.commit()
    except sqlite3.Error as e:
        print(f"❌ Error al actualizar el embedding del párrafo {id_parrafo}: {e}")
    finally:
        conn.close()

def obtener_parrafos_para_consulta(
    metodo_extraccion=None,
    tipo_extraccion=None,
    estrategia_segmentacion=None,
    idioma='es',
    modelo_embedding=None,
    id_fichero=None
):
    """
    Recupera los párrafos de la base de datos filtrando por los parámetros dados.
    Devuelve una lista de diccionarios con los campos relevantes.
    """
    conn = connect_to_db()
    if not conn:
        return []
    cursor = conn.cursor()
    try:
        query = """
            SELECT P.texto, P.embedding, F.nombreOriginal, P.id_parrafo
            FROM Parrafos P
            JOIN Ficheros F ON P.id_fichero = F.Id
            WHERE 1=1 and F.Id in (60,61)
        """
        params = []
        if modelo_embedding:
            query += " AND P.modelo_embedding = ?"
            params.append(modelo_embedding)
        if idioma:
            query += " AND P.idioma = ?"
            params.append(idioma)
        if estrategia_segmentacion:
            query += " AND P.estrategia_segmentacion = ?"
            params.append(estrategia_segmentacion)
        if tipo_extraccion:
            query += " AND P.tipo_extraccion = ?"
            params.append(tipo_extraccion)
        if metodo_extraccion:
            query += " AND P.metodo_extraccion = ?"
            params.append(metodo_extraccion)
        if id_fichero:
            query += " AND P.id_fichero = ?"
            params.append(id_fichero)
        cursor.execute(query, params)
        rows = cursor.fetchall()
        return [
            {
                "texto": row[0],
                "embedding": row[1],
                "nombreOriginal": row[2],
                "id_parrafo": row[3]
            }
            for row in rows
        ]
    except Exception as e:
        print(f"❌ Error al obtener párrafos para consulta: {e}")
        return []
    finally:
        conn.close()

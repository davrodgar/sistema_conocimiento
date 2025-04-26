"""Este módulo gestiona la interacción con Apache Tika y el procesamiento de documentos."""

import os
import time
import shutil
import subprocess
import json
import sqlite3
from datetime import datetime
import requests
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

# Directorios
BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))

INPUT_DIR = os.path.join(BASE_DIR, "data", "input")
PROCESSED_DIR = os.path.join(BASE_DIR, "data", "processed")
METADATA_DIR = os.path.join(BASE_DIR, "data", "knowledge")

# Crear subcarpeta para los archivos originales procesados
ORIGINAL_DIR = os.path.join(PROCESSED_DIR, "original")
os.makedirs(ORIGINAL_DIR, exist_ok=True)

# Ruta al archivo JAR de Tika Server
TIKA_JAR_PATH = os.path.join(BASE_DIR, "src/tools", "tika-server-standard-3.1.0.jar")
# URL del servidor Tika
TIKA_SERVER = "http://localhost:9998/tika"

ACCEPT_FORMAT = "text/plain"  # Cambia valor según formato ("application/json" o "text/plain")

# Ruta a la base de datos SQLite
DB_PATH = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "../data/sistema_conocimiento.db")
)

def connect_to_db():
    """
    Establece una conexión con la base de datos SQLite.

    :return: Objeto de conexión a la base de datos si existe, de lo contrario None.
    """
    if not os.path.exists(DB_PATH):
        print(f"❌ No se encontró la base de datos en: {DB_PATH}")
        return None
    return sqlite3.connect(DB_PATH)

# Comando para iniciar el servidor Tika
def start_tika_server():
    """
    Inicia el servidor Apache Tika utilizando el archivo JAR especificado.

    :return: Objeto del proceso si el servidor se inicia correctamente, de lo contrario None.
    """
    if not os.path.exists(TIKA_JAR_PATH):
        print(f"❌ No se encontró el archivo JAR de Tika en: {TIKA_JAR_PATH}")
        return None

    try:
        print("🚀 Iniciando Apache Tika Server...")
        process = subprocess.Popen(["java", "-jar", TIKA_JAR_PATH])
        print("✅ Apache Tika Server iniciado.")
        return process
    except (OSError, subprocess.SubprocessError) as e:
        print(f"❌ Error al iniciar Apache Tika Server: {e}")
        return None

# Procesamiento de documentos
def process_document(file_path, accept_format):
    """
    Procesa un documento usando Apache Tika y guarda la salida en el formato especificado.
    Antes de procesar, verifica si ya existe en la base de datos y solicita confirmación al usuario.
    """
    file_name = os.path.basename(file_path)
    base_name, file_extension = os.path.splitext(file_name)  # Separar el nombre base y la extensión
    metodo_extraccion = f"TIKA_{accept_format.replace('/', '_')}"  # Formato método de extracción
    fichero_generado = None  # Inicializar la variable
    tipo_extraccion = None  # Inicializar la variable

    # Comprobar si el archivo ya existe en la base de datos
    existing_id = check_existing_fichero(file_name, file_extension, metodo_extraccion)
    if existing_id:
        print(f"⚠️ El archivo '{file_name}' ya existe en BBDD con mismo tipo y método extracción.")
        user_input = input("¿Desea procesarlo nuevamente? (s/n): ").strip().lower()
        if user_input != 's':
            print(f"⏩ Procesamiento cancelado por el usuario para el archivo: {file_name}")
            return
        else:
            # Eliminar el registro anterior
            db_conn = sqlite3.connect(DB_PATH)
            cursor = db_conn.cursor()
            cursor.execute("DELETE FROM Ficheros WHERE Id = ?", (existing_id,))
            db_conn.commit()
            db_conn.close()
            print(f"🗑️ Registro anterior eliminado para el archivo: {file_name}")

    # Procesar el archivo con Apache Tika
    start_time = time.time()

    try:
        # Intentar varias veces si el archivo está bloqueado
        for _ in range(5):  # Intentar hasta 5 veces
            try:
                # Configurar encabezados para la solicitud
                headers = {
                    "Content-Type": "application/octet-stream",
                    "Accept": accept_format,  # Usar el valor pasado como argumento
                    "Accept-Charset": "UTF-8"  # Solicitar que la respuesta esté en UTF-8
                }
                with open(file_path, "rb") as f:
                    response = requests.put(TIKA_SERVER, data=f, headers=headers, timeout=10)
                if response.status_code == 200:
                    # Guardar la respuesta completa de Tika en un archivo RAW
                    # sanitized_accept_format = sanitize_filename(accept_format)
                    output_raw_file = os.path.join(
                        PROCESSED_DIR,
                        f"{base_name}_{metodo_extraccion}_Response.raw"
                    )
                    output_raw_file = os.path.join(
                        PROCESSED_DIR,
                        f"{base_name}_{metodo_extraccion}_Response.raw"
                    )
                    with open(output_raw_file, "w", encoding="utf-8") as f:
                        f.write(response.text)
                    print(f"✅ Respuesta completa de Tika guardada como: {output_raw_file}")

                    # Manejar la salida según el formato solicitado
                    if accept_format == "application/json":
                        # Extraer el contenido de "X-TIKA:content" y guardar como archivo HTML
                        tika_response = json.loads(response.text)
                        content_html = tika_response.get("X-TIKA:content", "")
                        if content_html.strip():
                            output_html_file = os.path.join(
                                                    PROCESSED_DIR,
                                                    f"{base_name}_{metodo_extraccion}_Content.html"
                                                    )
                            with open(output_html_file, "w", encoding="utf-8") as f:
                                f.write(content_html)
                            print(f"✅ Contenido HTML extraído guardado como: {output_html_file}")
                            fichero_generado = output_html_file
                            tipo_extraccion = ".html"
                        else:
                            print(
                                "⚠️ No se encontró contenido en 'X-TIKA:content' "
                                f"para el archivo: {file_name}"
                                )
                            return
                    elif accept_format == "text/plain":
                        # Guardar el contenido como archivo de texto
                        output_txt_file = os.path.join(
                                                PROCESSED_DIR,
                                                f"{base_name}_{metodo_extraccion}_Content.txt"
                                                )
                        with open(output_txt_file, "w", encoding="utf-8") as f:
                            f.write(response.text)
                        print(f"✅ Contenido de texto extraído guardado como: {output_txt_file}")
                        fichero_generado = output_txt_file
                        tipo_extraccion = ".txt"

                    # Mover el archivo original a la carpeta de procesados/original
                    shutil.move(file_path, os.path.join(ORIGINAL_DIR, file_name))
                    print(f"✅ Documento procesado y movido a: {ORIGINAL_DIR}")

                    # Añadir registro a la base de datos
                    tiempo_extraccion = int(time.time() - start_time)
                    add_fichero_record(
                        nombre_original=file_name,
                        tipo_original=file_extension,
                        metodo_extraccion=metodo_extraccion,
                        fichero_generado=fichero_generado,
                        tipo_extraccion=tipo_extraccion,
                        tiempo_extraccion=tiempo_extraccion
                    )
                else:
                    print(
                            "⚠️ No se pudo extraer texto del archivo: {file_name}. "
                            f"Código de estado: {response.status_code}"
                        )
                break  # Salir del bucle si se procesa correctamente
            except PermissionError:
                print(f"⚠️ Archivo en uso, reintentando: {file_name}")
                time.sleep(1)  # Esperar 1 segundo antes de reintentar
        else:
            print(f"❌ No se pudo procesar el archivo después de varios intentos: {file_name}")
    except Exception as e:
        print(f"❌ Error procesando {file_name}: {e}")

def sanitize_filename(value):
    """
    Reemplaza caracteres no válidos en nombres de archivos por un guion bajo.
    """
    return value.replace("/", "_").replace("\\", "_").replace(":", "_").replace("*", "_") \
                .replace("?", "_").replace("\"", "_").replace("<", "_").replace(">", "_") \
                .replace("|", "_")

def add_fichero_record(
        nombre_original, tipo_original, metodo_extraccion, fichero_generado, tipo_extraccion,
        tiempo_extraccion, observaciones=None
        ):
    """
    Añade un registro a la tabla Ficheros de la base de datos.

    :param DB_PATH: Ruta a la base de datos SQLite.
    :param nombre_original: Nombre original del archivo.
    :param tipo_original: Extensión del archivo original.
    :param metodo_extraccion: Método de extracción utilizado.
    :param fichero_generado: Ruta del fichero generado tras la extracción.
    :param tipo_extraccion: Tipo de extracción (formato solicitado).
    :param tiempo_extraccion: Tiempo que tomó la extracción en segundos.
    :param observaciones: Observaciones adicionales (opcional).
    """
    db_conn = sqlite3.connect(DB_PATH)
    cursor = db_conn.cursor()

    try:
        # Extraer solo el nombre del fichero generado (sin la ruta)
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
        db_conn.commit()
        print(f"✅ Registro añadido a la base de datos para el archivo: {nombre_original}")
    except Exception as e:
        print(f"❌ Error al añadir el registro a la base de datos: {e}")
    finally:
        db_conn.close()

def check_existing_fichero(nombre_original, tipo_original, metodo_extraccion):
    """
    Comprueba si ya existe un fichero con el mismo nombre, tipo original y método de extracción.

    :param DB_PATH: Ruta a la base de datos SQLite.
    :param nombre_original: Nombre original del archivo.
    :param tipo_original: Extensión del archivo original.
    :param metodo_extraccion: Método de extracción utilizado.
    :return: El ID del registro existente si se encuentra, de lo contrario None.
    """
    db_conn = sqlite3.connect(DB_PATH)
    cursor = db_conn.cursor()

    try:
        query = """
           SELECT Id FROM Ficheros
           WHERE nombreOriginal = ? AND tipoOriginal = ? AND metodoExtraccion = ?
        """
        params = (nombre_original, tipo_original, metodo_extraccion)
        print("🔍 Ejecutando consulta SQL: {query.strip()} "
              f"con los parametros: {params}")  # Traza de la consulta
        cursor.execute(query, params)
        result = cursor.fetchone()
        return result[0] if result else None
    except Exception as e:
        print(f"❌ Error al comprobar el registro en la base de datos: {e}")
        return None
    finally:
        db_conn.close()

# Monitor de la carpeta de entrada
class WatcherHandler(FileSystemEventHandler):
    """
    Clase que maneja eventos del sistema de archivos para monitorear la carpeta de entrada.
    
    Detecta la creación de nuevos archivos y los procesa automáticamente utilizando Apache Tika.
    """
    def on_created(self, event):
        if not event.is_directory:
            process_document(event.src_path, ACCEPT_FORMAT)

if __name__ == "__main__":
    print(f"📂 Ruta a la base de datos SQLite: {DB_PATH}")  # Traza de la ruta a la base de datos
    tika_process = start_tika_server()  # Guardar el proceso de Tika

    print(f"📂 El script se está ejecutando en: {os.getcwd()}")
    os.makedirs(INPUT_DIR, exist_ok=True)
    os.makedirs(PROCESSED_DIR, exist_ok=True)
    os.makedirs(METADATA_DIR, exist_ok=True)

    print(f"📂 Ruta de entrada (INPUT_DIR): {os.path.abspath(INPUT_DIR)}")
    print(f"📂 Ruta de procesados (PROCESSED_DIR): {os.path.abspath(PROCESSED_DIR)}")
    print(f"📂 Ruta de metadatos (METADATA_DIR): {os.path.abspath(METADATA_DIR)}")

    # Ejemplo de uso de la conexión a la base de datos
    conn = connect_to_db()
    if conn:
        print("✅ Conexión exitosa a la base de datos.")
        conn.close()

    # Listar archivos en la carpeta de entrada
    print("📋 Archivos encontrados en la carpeta de entrada:")
    for input_file_name in os.listdir(INPUT_DIR):
        input_file_path = os.path.join(INPUT_DIR, input_file_name)
        if os.path.isfile(input_file_path):
            print(f"  - {input_file_name}")
            process_document(input_file_path, ACCEPT_FORMAT)

    event_handler = WatcherHandler()
    observer = Observer()
    observer.schedule(event_handler, path=INPUT_DIR, recursive=False)
    observer.start()

    print("🔍 Monitoreando la carpeta de entrada...")
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n🛑 Deteniendo el script...")
    finally:
        if tika_process:
            print("🛑 Deteniendo Apache Tika Server...")
            tika_process.terminate()  # Detener el proceso de Tika
        observer.stop()
    observer.join()
    
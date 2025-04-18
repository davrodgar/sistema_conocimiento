import os
import time
import shutil
import json
import pdfplumber
import sqlite3
from datetime import datetime
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

# Directorios
BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))

INPUT_DIR = os.path.join(BASE_DIR, "data", "input")
PROCESSED_DIR = os.path.join(BASE_DIR, "data", "processed")
METADATA_DIR = os.path.join(BASE_DIR, "data", "knowledge")

# Ruta a la base de datos SQLite
DB_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), "../data/sistema_conocimiento.db"))

# Crear directorios si no existen
os.makedirs(INPUT_DIR, exist_ok=True)
os.makedirs(PROCESSED_DIR, exist_ok=True)
os.makedirs(METADATA_DIR, exist_ok=True)

# Crear subcarpeta para los archivos originales procesados
ORIGINAL_DIR = os.path.join(PROCESSED_DIR, "original")
os.makedirs(ORIGINAL_DIR, exist_ok=True)

def connect_to_db():
    if not os.path.exists(DB_PATH):
        print(f"❌ No se encontró la base de datos en: {DB_PATH}")
        return None
    return sqlite3.connect(DB_PATH)

def check_existing_fichero(DB_PATH, nombre_original, tipo_original, metodo_extraccion):
    """
    Comprueba si ya existe un fichero con el mismo nombre, tipo original y método de extracción.

    :param DB_PATH: Ruta a la base de datos SQLite.
    :param nombre_original: Nombre original del archivo.
    :param tipo_original: Extensión del archivo original.
    :param metodo_extraccion: Método de extracción utilizado.
    :return: El ID del registro existente si se encuentra, de lo contrario None.
    """
    conn = sqlite3.connect(DB_PATH)
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
    except Exception as e:
        print(f"❌ Error al comprobar el registro en la base de datos: {e}")
        return None
    finally:
        conn.close()

def add_fichero_record(DB_PATH, nombre_original, tipo_original, metodo_extraccion, fichero_generado, tipo_extraccion, tiempo_extraccion, observaciones=None):
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
    conn = sqlite3.connect(DB_PATH)
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
    except Exception as e:
        print(f"❌ Error al añadir el registro a la base de datos: {e}")
    finally:
        conn.close()

# Función para extraer texto de PDFs usando pdfplumber
def extract_text_from_pdf(file_path):
    try:
        texto_completo = ""
        with pdfplumber.open(file_path) as pdf:
            for pagina in pdf.pages:
                texto_pagina = pagina.extract_text()
                if texto_pagina:
                    texto_completo += texto_pagina.strip() + "\n\n"  # Separar páginas con doble salto de línea
        return texto_completo.strip()
    except Exception as e:
        print(f"❌ Error al extraer texto del PDF {file_path}: {e}")
        return ""

# Procesamiento de documentos
def process_document(file_path):
    file_name = os.path.basename(file_path)
    base_name, file_extension = os.path.splitext(file_name)
    metodo_extraccion = "PDFPlumber"
    print(f"📂 Procesando archivo: {file_name}")

    # Comprobar si el archivo ya existe en la base de datos
    existing_id = check_existing_fichero(DB_PATH, file_name, file_extension, metodo_extraccion)
    if existing_id:
        print(f"⚠️ El archivo '{file_name}' ya existe en la base de datos con el mismo tipo y método de extracción.")
        return

    try:
        start_time = time.time()
        for _ in range(5):
            try:
                if file_extension.lower() == ".pdf":
                    text = extract_text_from_pdf(file_path)
                else:
                    print(f"⚠️ El archivo {file_name} no es un PDF. Solo se procesan archivos PDF.")
                    return

                if text:
                    output_raw_file = os.path.join(PROCESSED_DIR, f"{base_name}{file_extension}_PDFPlumber_Response.raw")
                    with open(output_raw_file, "w", encoding="utf-8") as f:
                        f.write(text)
                    print(f"✅ Respuesta completa de Tika simulada guardada como: {output_raw_file}")

                    output_txt_file = os.path.join(PROCESSED_DIR, f"{base_name}{file_extension}_PDFPlumber_Content.txt")
                    with open(output_txt_file, "w", encoding="utf-8") as f:
                        f.write(text)
                    print(f"✅ Contenido de texto extraído guardado como: {output_txt_file}")

                    # Mover el archivo original a la carpeta de procesados/original
                    shutil.move(file_path, os.path.join(ORIGINAL_DIR, file_name))
                    print(f"✅ Documento procesado y movido a: {ORIGINAL_DIR}")

                    tiempo_extraccion = int(time.time() - start_time)
                    add_fichero_record(
                        DB_PATH,
                        nombre_original=file_name,
                        tipo_original=file_extension,
                        metodo_extraccion=metodo_extraccion,
                        fichero_generado=output_txt_file,
                        tipo_extraccion=".txt",
                        tiempo_extraccion=tiempo_extraccion
                    )
                else:
                    print(f"⚠️ No se pudo extraer texto del archivo: {file_name}")
                break
            except PermissionError:
                print(f"⚠️ Archivo en uso, reintentando: {file_name}")
                time.sleep(1)  # Esperar 1 segundo antes de reintentar
        else:
            print(f"❌ No se pudo procesar el archivo después de varios intentos: {file_name}")
    except Exception as e:
        print(f"❌ Error procesando {file_name}: {e}")

# Monitor de la carpeta de entrada
class WatcherHandler(FileSystemEventHandler):
    def on_created(self, event):
        if not event.is_directory:
            process_document(event.src_path)

if __name__ == "__main__":
    print(f"📂 El script se está ejecutando en: {os.getcwd()}")
    print(f"📂 Ruta de entrada (INPUT_DIR): {os.path.abspath(INPUT_DIR)}")
    print(f"📂 Ruta de procesados (PROCESSED_DIR): {os.path.abspath(PROCESSED_DIR)}")
    print(f"📂 Ruta de metadatos (METADATA_DIR): {os.path.abspath(METADATA_DIR)}")

    # Listar archivos en la carpeta de entrada
    print("📋 Archivos encontrados en la carpeta de entrada:")
    for file_name in os.listdir(INPUT_DIR):
        file_path = os.path.join(INPUT_DIR, file_name)
        if os.path.isfile(file_path):
            print(f"  - {file_name}")
            process_document(file_path)  # Procesar archivos existentes

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
        observer.stop()
    observer.join()
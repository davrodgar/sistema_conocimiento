"""
Módulo para procesar archivos PDF utilizando la biblioteca pdfplumber.

Este módulo incluye funciones para extraer texto de archivos PDF, verificar si ya han sido
procesados mediante una base de datos SQLite, y almacenar los resultados en archivos procesados.
También incluye un monitor para detectar nuevos archivos en una carpeta de entrada y procesarlos
automáticamente.
"""
import os
import time
import shutil
import pdfplumber
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

# Importar funciones de db_utils
from db_utils import check_existing_fichero, add_fichero_record

# Directorios
BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))

INPUT_DIR = os.path.join(BASE_DIR, "data", "input")
PROCESSED_DIR = os.path.join(BASE_DIR, "data", "processed")
METADATA_DIR = os.path.join(BASE_DIR, "data", "knowledge")

# Crear directorios si no existen
os.makedirs(INPUT_DIR, exist_ok=True)
os.makedirs(PROCESSED_DIR, exist_ok=True)
os.makedirs(METADATA_DIR, exist_ok=True)

# Crear subcarpeta para los archivos originales procesados
ORIGINAL_DIR = os.path.join(PROCESSED_DIR, "original")
os.makedirs(ORIGINAL_DIR, exist_ok=True)

# Función para extraer texto de PDFs usando pdfplumber
def extract_text_from_pdf(input_file_path):
    """
    Extrae el texto de un archivo PDF utilizando la biblioteca pdfplumber.

    :param input_file_path: Ruta al archivo PDF de entrada.
    :return: El texto extraído del PDF como una cadena. Si ocurre un error, 
    devuelve una cadena vacía.
    """
    try:
        texto_completo = ""
        with pdfplumber.open(input_file_path) as pdf:
            for pagina in pdf.pages:
                texto_pagina = pagina.extract_text()
                if texto_pagina:
                    texto_completo += texto_pagina.strip() + "\n\n"
                    # Separar páginas con doble salto de línea
        return texto_completo.strip()
    except Exception as e:
        print(f"❌ Error al extraer texto del PDF {input_file_path}: {e}")
        return ""

# Procesamiento de documentos
def process_document(input_file_path):
    """
    Procesa un archivo PDF verificando si ya existe en la base de datos, extrayendo su texto
    y almacenando los resultados en archivos procesados.

    :param input_file_path: Ruta al archivo PDF de entrada.
    :return: None. Realiza operaciones de procesamiento y almacenamiento.
    """
    input_file_name = os.path.basename(input_file_path)
    base_name, file_extension = os.path.splitext(input_file_name)
    metodo_extraccion = "PDFPlumber"
    print(f"📂 Procesando archivo: {input_file_name}")

    # Comprobar si el archivo ya existe en la base de datos
    existing_id = check_existing_fichero(input_file_name, file_extension, metodo_extraccion)
    if existing_id:
        print(f"⚠️ El archivo '{input_file_name}' ya existe en la base de datos "
              f"con el mismo tipo y método de extracción.")
        return

    try:
        start_time = time.time()
        for _ in range(5):
            try:
                if file_extension.lower() == ".pdf":
                    text = extract_text_from_pdf(input_file_path)
                else:
                    print(f"⚠️ El archivo {input_file_name} no es un PDF. "
                          f"Solo se procesan archivos PDF.")
                    return

                if text:
                    output_raw_file = os.path.join(
                                        PROCESSED_DIR,
                                        f"{base_name}{file_extension}_PDFPlumber_Response.raw")
                    with open(output_raw_file, "w", encoding="utf-8") as f:
                        f.write(text)
                    print(f"✅ Respuesta completa de Tika simulada guardada como: {output_raw_file}")

                    output_txt_file = os.path.join(
                                        PROCESSED_DIR,
                                        f"{base_name}{file_extension}_PDFPlumber_Content.txt")
                    with open(output_txt_file, "w", encoding="utf-8") as f:
                        f.write(text)
                    print(f"✅ Contenido de texto extraído guardado como: {output_txt_file}")

                    # Mover el archivo original a la carpeta de procesados/original
                    shutil.move(input_file_path, os.path.join(ORIGINAL_DIR, input_file_name))
                    print(f"✅ Documento procesado y movido a: {ORIGINAL_DIR}")

                    tiempo_extraccion = int(time.time() - start_time)
                    add_fichero_record(
                        nombre_original=input_file_name,
                        tipo_original=file_extension,
                        metodo_extraccion=metodo_extraccion,
                        fichero_generado=output_txt_file,
                        tipo_extraccion=".txt",
                        tiempo_extraccion=tiempo_extraccion
                    )
                else:
                    print(f"⚠️ No se pudo extraer texto del archivo: {input_file_name}")
                break
            except PermissionError:
                print(f"⚠️ Archivo en uso, reintentando: {input_file_name}")
                time.sleep(1)  # Esperar 1 segundo antes de reintentar
        else:
            print(f"❌ No se pudo procesar el archivo después de varios intentos: {input_file_name}")
    except Exception as e:
        print(f"❌ Error procesando {input_file_name}: {e}")

# Monitor de la carpeta de entrada
class WatcherHandler(FileSystemEventHandler):
    """
    Clase que maneja eventos del sistema de archivos para monitorear la carpeta de entrada.

    Detecta la creación de nuevos archivos en la carpeta de entrada y los procesa
    utilizando la función `process_document`.
    """
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

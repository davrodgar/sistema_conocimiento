import os
import time
import shutil
import requests
import subprocess
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
from pdfminer.high_level import extract_text
from docx import Document

# Directorios
BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))

INPUT_DIR = os.path.join(BASE_DIR, "data", "input")
PROCESSED_DIR = os.path.join(BASE_DIR, "data", "processed")
METADATA_DIR = os.path.join(BASE_DIR, "data", "knowledge")
# Ruta al archivo JAR de Tika Server

TIKA_JAR_PATH = os.path.join(BASE_DIR, "src/tools", "tika-server-standard-3.1.0.jar")
# URL del servidor Tika
TIKA_SERVER = "http://localhost:9998/tika"

# Comando para iniciar el servidor Tika
def start_tika_server():
    if not os.path.exists(TIKA_JAR_PATH):
        print(f"❌ No se encontró el archivo JAR de Tika en: {TIKA_JAR_PATH}")
        return None

    try:
        print("🚀 Iniciando Apache Tika Server...")
        process = subprocess.Popen(["java", "-jar", TIKA_JAR_PATH])
        print("✅ Apache Tika Server iniciado.")
        return process
    except Exception as e:
        print(f"❌ Error al iniciar Apache Tika Server: {e}")
        return None

# Función para extraer texto de PDFs
def extract_text_from_pdf(file_path):
    return extract_text(file_path)

# Función para extraer texto de DOCX
def extract_text_from_docx(file_path):
    doc = Document(file_path)
    return "\n".join([p.text for p in doc.paragraphs])

# Función para extraer texto de cualquier archivo con Apache Tika
def extract_text_from_tika(file_path):
    headers = {"Content-Type": "application/octet-stream"}
    with open(file_path, "rb") as f:
        response = requests.put(TIKA_SERVER + "/tika", data=f, headers=headers)
        return response.text if response.status_code == 200 else ""

# Procesamiento de documentos
def process_document(file_path):
    file_name = os.path.basename(file_path)
    text = ""
    print(f"📂 Procesando archivo: {file_name}")  # Traza para confirmar el archivo procesado
    try:
        # Intentar varias veces si el archivo está bloqueado
        for _ in range(5):  # Intentar hasta 5 veces
            try:
                if file_path.endswith(".pdf"):
                    text = extract_text_from_pdf(file_path)
                elif file_path.endswith(".docx"):
                    text = extract_text_from_docx(file_path)
                elif file_path.endswith(".doc"):
                    text = extract_text_from_tika(file_path)
                else:
                    text = extract_text_from_tika(file_path)

                if text:
                    output_text_file = os.path.join(PROCESSED_DIR, file_name + ".txt")
                    with open(output_text_file, "w", encoding="utf-8") as f:
                        f.write(text)

                    # Mover documento procesado
                    shutil.move(file_path, os.path.join(PROCESSED_DIR, file_name))
                    print(f"✅ Documento procesado: {file_name}")
                else:
                    print(f"⚠️ No se pudo extraer texto del archivo: {file_name}")
                break  # Salir del bucle si se procesa correctamente
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
    tika_process = start_tika_server()  # Guardar el proceso de Tika

    
    print(f"📂 El script se está ejecutando en: {os.getcwd()}")
    os.makedirs(INPUT_DIR, exist_ok=True)
    os.makedirs(PROCESSED_DIR, exist_ok=True)
    os.makedirs(METADATA_DIR, exist_ok=True)

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
        if tika_process:
            print("🛑 Deteniendo Apache Tika Server...")
            tika_process.terminate()  # Detener el proceso de Tika
        observer.stop()
    observer.join()

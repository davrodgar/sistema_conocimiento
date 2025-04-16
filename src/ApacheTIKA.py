import os
import time
import shutil
import requests
import subprocess
import json
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

ACCEPT_FORMAT = "text/plain"  # Cambia este valor según el formato deseado ("application/json" o "text/plain")

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

# Procesamiento de documentos
def process_document(file_path, accept_format):
    """
    Procesa un documento usando Apache Tika y guarda la salida en el formato especificado.
    
    :param file_path: Ruta del archivo a procesar.
    :param accept_format: Formato de salida solicitado a Tika ("application/json" o "text/plain").
    """
    file_name = os.path.basename(file_path)
    base_name, file_extension = os.path.splitext(file_name)  # Separar el nombre base y la extensión
    print(f"📂 Procesando archivo: {file_name} con Accept: {accept_format}")  # Traza para confirmar el archivo procesado

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
                    response = requests.put(TIKA_SERVER, data=f, headers=headers)
                
                if response.status_code == 200:
                    # Guardar la respuesta completa de Tika en un archivo RAW
                    sanitized_accept_format = sanitize_filename(accept_format)  # Limpia el formato
                    output_raw_file = os.path.join(PROCESSED_DIR, f"{base_name}{file_extension}_TIKA_{sanitized_accept_format}_Response.raw")
                    with open(output_raw_file, "w", encoding="utf-8") as f:
                        f.write(response.text)
                    print(f"✅ Respuesta completa de Tika guardada como: {output_raw_file}")

                    # Manejar la salida según el formato solicitado
                    if accept_format == "application/json":
                        # Extraer el contenido de "X-TIKA:content" y guardar como archivo HTML
                        tika_response = json.loads(response.text)
                        content_html = tika_response.get("X-TIKA:content", "")
                        if content_html.strip():
                            output_html_file = os.path.join(PROCESSED_DIR, f"{base_name}{file_extension}_TIKA_{sanitized_accept_format}_Content.html")
                            with open(output_html_file, "w", encoding="utf-8") as f:
                                f.write(content_html)
                            print(f"✅ Contenido HTML extraído guardado como: {output_html_file}")
                        else:
                            print(f"⚠️ No se encontró contenido en 'X-TIKA:content' para el archivo: {file_name}")
                    elif accept_format == "text/plain":
                        # Guardar el contenido como archivo de texto
                        output_txt_file = os.path.join(PROCESSED_DIR, f"{base_name}{file_extension}_TIKA_{sanitized_accept_format}_Content.txt")
                        with open(output_txt_file, "w", encoding="utf-8") as f:
                            f.write(response.text)
                        print(f"✅ Contenido de texto extraído guardado como: {output_txt_file}")

                    # Mover el archivo original a la carpeta de procesados/original
                    shutil.move(file_path, os.path.join(ORIGINAL_DIR, file_name))
                    print(f"✅ Documento procesado y movido a: {ORIGINAL_DIR}")
                else:
                    print(f"⚠️ No se pudo extraer texto del archivo: {file_name}. Código de estado: {response.status_code}")
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
                .replace("?", "_").replace("\"", "_").replace("<", "_").replace(">", "_").replace("|", "_")

# Monitor de la carpeta de entrada
class WatcherHandler(FileSystemEventHandler):
    def on_created(self, event):
        if not event.is_directory:
            process_document(event.src_path, ACCEPT_FORMAT)

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
            process_document(file_path, ACCEPT_FORMAT)

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

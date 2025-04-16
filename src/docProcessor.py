import os
import time
import shutil
from docx import Document
import win32com.client
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

# Directorios
BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))

INPUT_DIR = os.path.join(BASE_DIR, "data", "input")
PROCESSED_DIR = os.path.join(BASE_DIR, "data", "processed")
METADATA_DIR = os.path.join(BASE_DIR, "data", "knowledge")

# Crear directorios si no existen
os.makedirs(INPUT_DIR, exist_ok=True)
os.makedirs(PROCESSED_DIR, exist_ok=True)
os.makedirs(METADATA_DIR, exist_ok=True)

# Función para extraer texto de documentos DOCX usando python-docx
def extract_text_from_docx(file_path):
    try:
        doc = Document(file_path)
        texto_completo = "\n\n".join([p.text.strip() for p in doc.paragraphs if p.text.strip()])
        return texto_completo.strip()
    except Exception as e:
        import traceback
        print(f"❌ Error al extraer texto del documento {file_path}: {e}")
        traceback.print_exc()  # Imprime el rastreo completo del error
        return ""

# Función para extraer texto de documentos DOC usando win32com
def extract_text_from_doc(file_path):
    try:
        word = win32com.client.Dispatch("Word.Application")
        doc = word.Documents.Open(file_path)
        text = doc.Content.Text
        doc.Close()
        word.Quit()
        return text.strip()
    except Exception as e:
        print(f"❌ Error al extraer texto del archivo DOC: {e}")
        return ""

# Procesamiento de documentos
def process_document(file_path):
    file_name = os.path.basename(file_path)
    base_name, file_extension = os.path.splitext(file_name)  # Separar el nombre base y la extensión
    print(f"📂 Procesando archivo: {file_name}")  # Traza para confirmar el archivo procesado

    try:
        # Intentar varias veces si el archivo está bloqueado
        for _ in range(5):  # Intentar hasta 5 veces
            try:
                if file_extension.lower() == ".docx":
                    # Extraer texto usando python-docx
                    text = extract_text_from_docx(file_path)
                elif file_extension.lower() == ".doc":
                    # Extraer texto usando win32com
                    text = extract_text_from_doc(file_path)
                else:
                    print(f"⚠️ El archivo {file_name} no es un documento DOC o DOCX. Solo se procesan estos formatos.")
                    return

                if text:
                    # Guardar el texto extraído en un archivo RAW
                    output_raw_file = os.path.join(PROCESSED_DIR, f"{base_name}{file_extension}_python-docx_Response.raw")
                    with open(output_raw_file, "w", encoding="utf-8") as f:
                        f.write(text)
                    print(f"✅ Respuesta completa guardada como: {output_raw_file}")

                    # Guardar el contenido como archivo de texto (simulando "text/plain")
                    output_txt_file = os.path.join(PROCESSED_DIR, f"{base_name}{file_extension}_python-docx_Content.txt")
                    with open(output_txt_file, "w", encoding="utf-8") as f:
                        f.write(text)
                    print(f"✅ Contenido de texto extraído guardado como: {output_txt_file}")

                    # Mover el archivo original a la carpeta de procesados
                    shutil.move(file_path, os.path.join(PROCESSED_DIR, file_name))
                    print(f"✅ Documento procesado y movido a: {PROCESSED_DIR}")
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
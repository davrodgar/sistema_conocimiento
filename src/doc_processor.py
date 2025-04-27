"""
Módulo docProcessor.py
-----------------------
Este módulo se encarga de procesar documentos en formato DOC y DOCX, extrayendo su contenido
y almacenando los resultados en una base de datos SQLite. También monitorea una carpeta de entrada
para procesar automáticamente nuevos archivos que se agreguen.

Funciones principales:
- extract_text_from_docx: Extrae texto de archivos DOCX usando python-docx.
- extract_text_from_doc: Extrae texto de archivos DOC usando win32com.
- process_document: Procesa un archivo, extrae su contenido y lo registra en la base de datos.
- WatcherHandler: Clase para monitorear la carpeta de entrada y procesar nuevos archivos.
"""

import os
import time
import shutil
import traceback
from docx import Document
import win32com.client
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

# Función para extraer texto de documentos DOCX usando python-docx
def extract_text_from_docx(input_file_path):
    """
    Extrae el texto de un archivo DOCX.

    Utiliza la biblioteca python-docx para leer el contenido del archivo y 
    concatenar los párrafos en un único texto.

    :param input_file_path: Ruta al archivo DOCX que se desea procesar.
    :return: Texto extraído del archivo como una cadena. 
        Si ocurre un error, devuelve una cadena vacía.
    """
    try:
        doc = Document(input_file_path)
        texto_completo = "\n\n".join([p.text.strip() for p in doc.paragraphs if p.text.strip()])
        return texto_completo.strip()
    except FileNotFoundError as e:
        print(f"❌ Archivo no encontrado: {input_file_path}. Error: {e}")
    except IOError as e:
        print(f"❌ Error de E/S al procesar el archivo {input_file_path}: {e}")
    except Exception as e:  # Captura general como último recurso
        print(f"❌ Error inesperado al extraer texto del documento {input_file_path}: {e}")
        traceback.print_exc()  # Usar traceback aquí
    return ""

# Función para extraer texto de documentos DOC usando win32com
def extract_text_from_doc(input_file_path):
    """
    Extrae el texto de un archivo DOC.

    Utiliza la biblioteca win32com para abrir el archivo DOC con Microsoft Word,
    leer su contenido y devolverlo como texto.

    :param input_file_path: Ruta al archivo DOC que se desea procesar.
    :return: Texto extraído del archivo como una cadena. Si ocurre un error, 
    devuelve una cadena vacía.
    """
    try:
        word = win32com.client.Dispatch("Word.Application")
        doc = word.Documents.Open(input_file_path)
        text = doc.Content.Text
        doc.Close()
        word.Quit()
        return text.strip()
    except FileNotFoundError as e:
        print(f"❌ Archivo no encontrado: {input_file_path}. Error: {e}")
    except IOError as e:
        print(f"❌ Error de E/S al procesar el archivo {input_file_path}: {e}")
    except Exception as e:  # Captura general como último recurso
        print(f"❌ Error inesperado al extraer texto del archivo DOC: {e}")
        traceback.print_exc()
    return ""

# Procesamiento de documentos
def process_document(input_file_path):
    """
        Procesa un archivo DOC o DOCX, extrae su contenido y lo registra en la base de datos.

        La función verifica si el archivo ya ha sido procesado previamente. Si no lo ha sido,
        extrae el texto del archivo, guarda el contenido en archivos de texto y RAW, mueve
        el archivo original a la carpeta de procesados y 
        registra la información en la base de datos.

        :param input_file_path: Ruta al archivo que se desea procesar.
        :return: None
    """
    input_file_name = os.path.basename(input_file_path)
    base_name, file_extension = os.path.splitext(input_file_name)
    metodo_extraccion = "python-docx"
    print(f"📂 Procesando archivo: {input_file_name}")

    # Comprobar si el archivo ya existe en la base de datos
    existing_id = check_existing_fichero(input_file_name, file_extension, metodo_extraccion)
    if existing_id:
        print(f"⚠️ El archivo '{input_file_name}' ya existe en la base de datos "
              f"con el mismo tipo y método de extracción.")
        return

    try:
        start_time = time.time()
        for _ in range(5):  # Intentar hasta 5 veces
            try:
                if file_extension.lower() == ".docx":
                    # Extraer texto usando python-docx
                    text = extract_text_from_docx(input_file_path)
                elif file_extension.lower() == ".doc":
                    # Extraer texto usando win32com
                    text = extract_text_from_doc(input_file_path)
                else:
                    print(f"⚠️ El archivo {input_file_name} no es un documento DOC o DOCX. "
                          f"Solo se procesan estos formatos.")
                    return

                if text:
                    # Guardar el texto extraído en un archivo RAW
                    output_raw_file = os.path.join(
                                        PROCESSED_DIR,
                                        f"{base_name}{file_extension}_python-docx_Response.raw"
                                        )
                    # Asegurarse de que el nombre del archivo no exceda los 255 caracteres
                    with open(output_raw_file, "w", encoding="utf-8") as f:
                        f.write(text)
                    print(f"✅ Respuesta completa guardada como: {output_raw_file}")

                    # Guardar el contenido como archivo de texto (simulando "text/plain")
                    output_txt_file = os.path.join(
                                            PROCESSED_DIR,
                                            f"{base_name}{file_extension}_python-docx_Content.txt"
                                            )
                    with open(output_txt_file, "w", encoding="utf-8") as f:
                        f.write(text)
                    print(f"✅ Contenido de texto extraído guardado como: {output_txt_file}")

                    # Mover el archivo original a la carpeta de procesados
                    shutil.move(input_file_path, os.path.join(PROCESSED_DIR, input_file_name))
                    print(f"✅ Documento procesado y movido a: {PROCESSED_DIR}")

                    # Añadir registro a la base de datos
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
                break  # Salir del bucle si se procesa correctamente
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
        Clase para manejar eventos de creación de archivos en una carpeta monitoreada.

        Esta clase extiende FileSystemEventHandler y se utiliza para detectar
        la creación de nuevos archivos en la carpeta de entrada. Cuando se detecta
        un nuevo archivo, se llama a la función process_document para procesarlo.

        Métodos:
        - on_created(event): Se ejecuta cuando se crea un archivo en la carpeta monitoreada.
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

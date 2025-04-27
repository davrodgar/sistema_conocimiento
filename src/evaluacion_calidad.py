"""
Módulo para evaluar la calidad de los documentos procesados.

Este módulo compara los documentos originales con los generados tras el procesamiento,
calculando métricas como la similitud, el texto perdido, los artefactos y el orden conservado.
También registra los resultados en un archivo de texto y utiliza una base de datos SQLite
para obtener información sobre los documentos procesados.
"""
import os
import re
import sqlite3
import unicodedata
from difflib import SequenceMatcher
from datetime import datetime
import time
from bs4 import BeautifulSoup
import win32com.client  # Importar pywin32 para interactuar con Microsoft Word

# Directorios base
PROCESSED_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "../data/processed"))
ORIGINAL_DIR = os.path.join(PROCESSED_DIR, "original")  # Ruta para los archivos originales
DB_PATH = os.path.abspath(
                os.path.join(os.path.dirname(__file__),
                            "../data/sistema_conocimiento.db"))
RESULTS_FILE = os.path.abspath(
                os.path.join(os.path.dirname(__file__),
                             "../data/resultados_comparaciones.txt"))

def html_to_text(html_content):
    """Convierte contenido HTML a texto plano."""
    soup = BeautifulSoup(html_content, "html.parser")
    return soup.get_text(separator="\n")

def normalize_text(text):
    """Normaliza el texto eliminando artefactos y caracteres no deseados."""
    text = re.sub(r'<[^>]+>', '', text)  # Eliminar etiquetas HTML residuales
    text = unicodedata.normalize("NFKC", text)  # Normalización Unicode
    text = re.sub(r'\s+', ' ', text)  # Reducir espacios múltiples
    text = re.sub(r'[^\w\s]', '', text)  # Eliminar puntuación
    return text.strip().lower()  # Convertir a minúsculas y eliminar espacios iniciales/finales

def similarity_ratio(original, extracted):
    """Calcula la similitud entre el texto original y el extraído."""
    return SequenceMatcher(None, original, extracted).ratio()

def read_original_text(file_path):
    """ 
        Recorta el texto del archivo original 
        eliminando elementos no relevantes utilizando Microsoft Word.
    """
    try:
        word = win32com.client.Dispatch("Word.Application")
        word.Visible = False

        # Abrir el archivo en Word
        doc = word.Documents.Open(file_path)
        text = doc.Content.Text  # Extraer solo el texto principal
        doc.Close()
        word.Quit()

        return normalize_text(text)
    except Exception as e:
        if 'word' in locals():
            word.Quit()
        print(f"Advertencia: No se pudo procesar el archivo {file_path}. Error: {e}")
        return ""

def evaluate_file(original_text, extracted_path, original_word_count, is_html=False):
    """Evalúa un archivo extraído comparándolo con el texto original."""
    with open(extracted_path, "r", encoding="utf-8") as f:
        extracted_text = f.read()
        if is_html:
            extracted_text = html_to_text(extracted_text)
        extracted_text = normalize_text(extracted_text)

    # Contar palabras en el texto extraído
    extracted_words = extracted_text.split()
    print(f"Palabras en fichero procesado: {len(extracted_words)}")

    # Convertir las palabras de ambos textos en conjuntos
    original_words_set = set(original_text.split())
    extracted_words_set = set(extracted_words)

    # Calcular las palabras adicionales (artefactos)
    palabras_extra = len(extracted_words_set - original_words_set)

    # Calcular la subsecuencia común más larga (LCS)
    matcher = SequenceMatcher(None, original_text.split(), extracted_text.split())
    lcs_length = sum(block.size for block in matcher.get_matching_blocks())
    orden_conservado = (lcs_length / max(len(original_text.split()), 1)) * 100

    # Métricas de evaluación
    similitud = similarity_ratio(original_text, extracted_text)
    palabras_perdidas = original_word_count - len(extracted_words)
    perdida = max(palabras_perdidas, 0) / max(original_word_count, 1) * 100

    return {
        "similitud": round(similitud * 100, 2),
        "texto_perdido": round(perdida, 2),
        "artefactos": palabras_extra,
        "orden_conservado": round(orden_conservado, 2)
    }

def get_files_from_db():
    """Obtiene los ficheros originales y generados desde la base de datos."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    query = """
    SELECT nombreOriginal, ficheroGenerado, metodoExtraccion, tipoExtraccion
    FROM Ficheros
    """
    cursor.execute(query)
    files = cursor.fetchall()
    conn.close()
    return files

def log_result(original_file, generated_file, start_time, duration, resultado,
               original_word_count, extracted_word_count):
    """Escribe el resultado de la comparación en un fichero."""
    with open(RESULTS_FILE, "a", encoding="utf-8") as f:
        f.write(f"{datetime.now()} | Original: {original_file} | Generado: {generated_file} | "
                f"Inicio: {start_time} | Duración: {duration:.2f}s | "
                f"Similitud: {resultado['similitud']}% | "
                f"Texto perdido: {resultado['texto_perdido']}% | "
                f"Artefactos: {resultado['artefactos']} | "
                f"Orden conservado: {resultado['orden_conservado']}% | "
                f"Palabras originales: {original_word_count} | "
                f"Palabras extraídas: {extracted_word_count} | "
                f"Método de extracción: {resultado['metodo_extraccion']} | "
                f"Tipo de extracción: {resultado['tipo_extraccion']}\n")

def count_words(file_path):
    """Cuenta el número de palabras en un archivo utilizando Microsoft Word."""
    try:
        word = win32com.client.Dispatch("Word.Application")
        word.Visible = False  # Ejecutar Word en segundo plano
        doc = word.Documents.Open(file_path)  # Abrir el archivo en Word
        word_count = doc.Words.Count  # Obtener el conteo de palabras
        doc.Close()  # Cerrar el documento
        word.Quit()  # Cerrar la aplicación de Word
        return word_count
    except Exception as e:
        if 'word' in locals():
            word.Quit()  # Asegurarse de cerrar Word en caso de error
        raise RuntimeError(f"Error al contar palabras en el archivo {file_path}: {e}") from e

def main():
    """
    Función principal para evaluar la calidad de los documentos procesados.

    Esta función:
    - Obtiene los archivos originales y generados desde la base de datos.
    - Agrupa los archivos generados por su archivo original correspondiente.
    - Evalúa cada archivo generado comparándolo con su archivo original.
    - Calcula métricas como similitud, texto perdido, artefactos y orden conservado.
    - Registra los resultados en un archivo de texto y los muestra en la consola.

    :return: None
    """

    resultados = []
    # extracciones_por_original = {}

    # Obtener los ficheros desde la base de datos
    files = get_files_from_db()

    # Agrupar los ficheros por nombreOriginal
    ficheros_por_original = {}
    for nombre_original, fichero_generado, metodo_extraccion, tipo_extraccion in files:
        # Filtrar archivos generados que no correspondan exactamente al archivo original
        if not fichero_generado.startswith(nombre_original):
            continue
        ficheros_por_original.setdefault(nombre_original, []).append({
            "fichero_generado": fichero_generado,
            "metodo_extraccion": metodo_extraccion,
            "tipo_extraccion": tipo_extraccion
        })

    # Procesar cada archivo original
    for original_file, extracciones in ficheros_por_original.items():
        print(f"Archivo original: {original_file}")
        print(f"Archivos generados asociados: {[e['fichero_generado'] for e in extracciones]}")
        original_path = os.path.join(ORIGINAL_DIR, original_file)
        if not os.path.exists(original_path):
            print(f"Archivo original no encontrado: {original_path}")
            continue

        # Leer el texto del archivo original
        original_text = read_original_text(original_path)

        # Contar palabras en el archivo original utilizando Microsoft Word
        original_word_count = count_words(original_path)
        print(f"Palabras en fichero original: {original_word_count}")

        for extraccion in list(extracciones):
            extracted_path = os.path.join(PROCESSED_DIR, extraccion["fichero_generado"])
            if not os.path.exists(extracted_path):
                print(f"Archivo extraído no encontrado: {extracted_path}")
                continue

            is_html = extraccion["tipo_extraccion"].lower() == "html"
            print(f"Procesando archivo original: {original_file}")
            print(f"Archivo extraído: {extraccion['fichero_generado']}")
            print(f"Método de extracción: {extraccion['metodo_extraccion']}")
            print(f"Tipo de extracción: {extraccion['tipo_extraccion']}")

            start_time = datetime.now()
            start_timestamp = time.time()
            resultado = evaluate_file(original_text, extracted_path, original_word_count, is_html)
            end_timestamp = time.time()
            duration = end_timestamp - start_timestamp

            resultado["documento"] = extraccion["fichero_generado"]
            resultado["metodo_extraccion"] = extraccion["metodo_extraccion"]
            resultado["tipo_extraccion"] = extraccion["tipo_extraccion"]
            resultados.append(resultado)

            # Registrar el resultado en el fichero
            extracted_word_count = (original_word_count
                                    - int(resultado["texto_perdido"] * original_word_count / 100)
                                    + resultado["artefactos"])
            log_result(original_file, extraccion["fichero_generado"],
                       start_time, duration, resultado, original_word_count, extracted_word_count)

    # Mostrar resultados de evaluación (opcional, si no se evalúan, no hay resultados)
    for r in resultados:
        print(f"Documento: {r['documento']}")
        print(f"  Similitud: {r['similitud']}%")
        print(f"  Texto perdido: {r['texto_perdido']}%")
        print(f"  Artefactos: {r['artefactos']}")
        print(f"  Orden conservado: {r['orden_conservado']}%")
        print(f"  Método de extracción: {r['metodo_extraccion']}")
        print(f"  Tipo de extracción: {r['tipo_extraccion']}")
        print()

if __name__ == "__main__":
    main()

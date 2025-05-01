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
import csv  # Importar el módulo csv
from bs4 import BeautifulSoup
import win32com.client  # Importar pywin32 para interactuar con Microsoft Word

# Directorios base
PROCESSED_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "../data/processed"))
ORIGINAL_DIR = os.path.join(PROCESSED_DIR, "original")  # Ruta para los archivos originales
DB_PATH = os.path.abspath(
                os.path.join(os.path.dirname(__file__),
                            "../data/sistema_conocimiento.db"))
RESULTS_FILE = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "../data/resultados_comparaciones.csv"))

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
        print(f"📂 Abriendo archivo original en Microsoft Word: {file_path}")
        word = win32com.client.Dispatch("Word.Application")
        word.Visible = False

        # Abrir el archivo en Word
        doc = word.Documents.Open(file_path)
        text = doc.Content.Text  # Extraer solo el texto principal
        doc.Close()
        word.Quit()
        print(f"✅ Archivo procesado correctamente: {file_path}")
        return normalize_text(text)
    except Exception as e:
        if 'word' in locals():
            word.Quit()
        print(f"❌ Advertencia: No se pudo procesar el archivo {file_path}. Error: {e}")
        return ""

def evaluate_file(original_text, extracted_path, original_word_count, is_html=False):
    """Evalúa un archivo extraído comparándolo con el texto original."""
    print(f"🔍 Evaluando archivo extraído: {extracted_path}")
    with open(extracted_path, "r", encoding="utf-8") as f:
        extracted_text = f.read()
        if is_html:
            print("🌐 Detectado formato HTML, convirtiendo a texto plano...")
            extracted_text = html_to_text(extracted_text)
        extracted_text = normalize_text(extracted_text)

    # Contar palabras en el texto extraído
    extracted_words = extracted_text.split()
    print(f"📊 Palabras en fichero procesado: {len(extracted_words)}")

    # Convertir las palabras de ambos textos en conjuntos
    original_words_set = set(original_text.split())
    extracted_words_set = set(extracted_words)

    # Calcular las palabras adicionales (artefactos)
    palabras_extra = len(extracted_words_set - original_words_set)
    print(f"🛠️ Artefactos detectados: {palabras_extra}")

    # Calcular la subsecuencia común más larga (LCS)
    matcher = SequenceMatcher(None, original_text.split(), extracted_text.split())
    lcs_length = sum(block.size for block in matcher.get_matching_blocks())
    orden_conservado = (lcs_length / max(len(original_text.split()), 1)) * 100
    print(f"🔗 Orden conservado calculado: {orden_conservado:.2f}%")

    # Métricas de evaluación
    similitud = similarity_ratio(original_text, extracted_text)
    palabras_perdidas = original_word_count - len(extracted_words)
    perdida = max(palabras_perdidas, 0) / max(original_word_count, 1) * 100
    print(f"📈 Similitud: {similitud * 100:.2f}%, Texto perdido: {perdida:.2f}%")

    # Calcular calidad total
    calidad_total = calcular_calidad_total(
        similitud * 100, perdida, orden_conservado, palabras_extra, original_word_count
    )

    return {
        "similitud": round(similitud * 100, 2),
        "texto_perdido": round(perdida, 2),
        "artefactos": palabras_extra,
        "orden_conservado": round(orden_conservado, 2),
        "calidad_total": calidad_total  # Agregar calidad total al resultado
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
    """Escribe el resultado de la comparación en un fichero CSV."""
    # Verificar si el archivo CSV existe
    file_exists = os.path.isfile(RESULTS_FILE)

    # Escribir los resultados en el archivo CSV
    with open(RESULTS_FILE, "a", newline='', encoding="utf-8") as f:
        writer = csv.writer(f)

        # Escribir las cabeceras si el archivo no existe
        if not file_exists:
            writer.writerow([
                "Fecha", "Archivo Original", "Archivo Generado", "Inicio", "Duración (s)",
                "Similitud (%)", "Texto Perdido (%)", "Artefactos", "Orden Conservado (%)",
                "Calidad Total (%)", "Palabras Originales", "Palabras Extraídas",
                "Método de Extracción", "Tipo de Extracción"
            ])

        # Escribir los datos
        writer.writerow([
            datetime.now(), original_file, generated_file, start_time, f"{duration:.2f}",
            resultado['similitud'], resultado['texto_perdido'], resultado['artefactos'],
            resultado['orden_conservado'], resultado['calidad_total'], original_word_count,
            extracted_word_count, resultado['metodo_extraccion'], resultado['tipo_extraccion']
        ])

    print(f"✅ Resultados registrados correctamente en {RESULTS_FILE}.")

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

def calcular_artefactos_normalizados(palabras_extra, original_word_count):
    """
    Normaliza el número de artefactos detectados en función del tamaño del documento original.
    
    :param palabras_extra: Número de palabras adicionales detectadas (artefactos).
    :param original_word_count: Número total de palabras en el texto original.
    :return: Porcentaje de artefactos normalizados.
    """
    if original_word_count == 0:
        return 0  # Evitar división por cero
    return (palabras_extra / original_word_count) * 100

def calcular_calidad_total(similitud, texto_perdido,
                           orden_conservado, palabras_extra, original_word_count):
    """
    Calcula un valor único de calidad total basado en los indicadores ponderados.
    
    :param similitud: Porcentaje de similitud entre el texto original y el extraído.
    :param texto_perdido: Porcentaje de texto perdido.
    :param orden_conservado: Porcentaje de orden conservado.
    :param palabras_extra: Número de palabras adicionales detectadas (artefactos).
    :param original_word_count: Número total de palabras en el texto original.
    :return: Valor único de calidad total.
    """
    # Normalizar artefactos
    artefactos_normalizados = calcular_artefactos_normalizados(palabras_extra, original_word_count)
    # Calcular calidad total
    calidad_total = (
        (0.40 * similitud) +
        (0.30 * (100 - texto_perdido)) +
        (0.20 * orden_conservado) +
        (0.10 * (100 - artefactos_normalizados))  # Penalización por artefactos
    )
    return round(calidad_total, 2)

def main():
    """
    Función principal para evaluar la calidad de los documentos procesados.
    """
    print("🚀 Iniciando evaluación de calidad de documentos...")
    resultados = []

    # Obtener los ficheros desde la base de datos
    files = get_files_from_db()

    # Agrupar los ficheros por nombreOriginal
    ficheros_por_original = {}
    for nombre_original, fichero_generado, metodo_extraccion, tipo_extraccion in files:
        if not fichero_generado.startswith(nombre_original):
            print(f"⚠️ Archivo generado '{fichero_generado}' "
                  f"no corresponde al original '{nombre_original}'.")
            continue
        ficheros_por_original.setdefault(nombre_original, []).append({
            "fichero_generado": fichero_generado,
            "metodo_extraccion": metodo_extraccion,
            "tipo_extraccion": tipo_extraccion
        })

    # Procesar cada archivo original
    for original_file, extracciones in ficheros_por_original.items():
        print(f"📂 Procesando archivo original: {original_file}")
        original_path = os.path.join(ORIGINAL_DIR, original_file)
        if not os.path.exists(original_path):
            print(f"❌ Archivo original no encontrado: {original_path}")
            continue

        # Leer el texto del archivo original
        try:
            original_text = read_original_text(original_path)
            print("✅ Texto del archivo original leído correctamente.")
        except Exception as e:
            print(f"❌ Error al leer el archivo original {original_file}: {e}")
            continue

        # Contar palabras en el archivo original
        try:
            original_word_count = count_words(original_path)
            print(f"📊 Palabras en el archivo original: {original_word_count}")
        except Exception as e:
            print(f"❌ Error al contar palabras en el archivo original {original_file}: {e}")
            continue

        for extraccion in extracciones:
            extracted_path = os.path.join(PROCESSED_DIR, extraccion["fichero_generado"])
            if not os.path.exists(extracted_path):
                print(f"❌ Archivo extraído no encontrado: {extracted_path}")
                continue

            print(f"🔍 Evaluando archivo extraído: {extraccion['fichero_generado']}")
            start_time = datetime.now()
            start_timestamp = time.time()
            try:
                resultado = evaluate_file(original_text, extracted_path, original_word_count,
                                          is_html=extraccion["tipo_extraccion"].lower() == "html")
                end_timestamp = time.time()
                duration = end_timestamp - start_timestamp
                print(f"✅ Evaluación completada en {duration:.2f} segundos.")
                # Unificar la impresión de calidad_total aquí
                print(
                    f"⭐ Calidad Total del archivo: {resultado['calidad_total']}%"                )
            except Exception as e:
                print(f"❌ Error al evaluar el archivo extraído {extraccion['fichero_generado']}: "
                      f"{e}")
                continue

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

    print("✅ Evaluación de calidad completada.")
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

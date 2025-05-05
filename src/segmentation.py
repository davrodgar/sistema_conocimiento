"""
Este módulo realiza la segmentación de archivos de texto y HTML en párrafos.

Funciones principales:
- limpiar_html: Limpia el contenido HTML y extrae texto relevante.
- segmentar_por_saltos: Divide el texto en párrafos usando saltos de línea.
- segmentar_por_titulo: Segmenta el texto en base a títulos detectados.
- detectar_idioma: Detecta el idioma de un texto.
- extraer_titulos: Extrae títulos del texto.
- procesar_archivos: Procesa los archivos en el directorio de entrada y guarda los resultados.

El módulo utiliza bibliotecas como BeautifulSoup y LangDetect para el procesamiento.
"""
import os
import re
import json
import time
from datetime import datetime
import pandas as pd
from bs4 import BeautifulSoup
from langdetect import detect, DetectorFactory, LangDetectException
from nltk.corpus import stopwords
from nltk.tokenize import word_tokenize
import nltk
from db_utils import obtener_metodo_tipo_extraccion

# Configuración inicial
DetectorFactory.seed = 0

PROCESSED_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "../data/processed"))
SEGMENTED_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "../data/segmented"))
os.makedirs(SEGMENTED_DIR, exist_ok=True)

# Expresiones regulares para detección de distintos tipos de títulos
TITULO_NUMERICO = re.compile(r"^\s*(\d+(\.\d+)*)\s+([A-Z][^:\n]*)$")
TITULO_LETRA = re.compile(r"^\s*([A-Za-z])\s+([A-Z][^:\n]*)$")
TITULO_ROMANO = re.compile(r"^\s*([IVXLCDMivxlcdm]+)\s+([A-Z][^:\n]*)$")
TITULO_MAYUSCULAS = re.compile(r"^[A-ZÁÉÍÓÚÜÑ\s]+\n*$")

# Validación de número romano bien formado
ROMAN_VALID = re.compile(
    r"^M{0,4}(CM|CD|D?C{0,3})(XC|XL|L?X{0,3})(IX|IV|V?I{0,3})$",
    re.IGNORECASE
)

# Descargar recursos necesarios de NLTK
nltk.download('stopwords')
nltk.download('punkt')

# Lista de stopwords en español
STOPWORDS = set(stopwords.words('spanish'))

# Función para limpiar HTML
def limpiar_html(texto):
    """
        Limpia el contenido HTML y extrae el texto relevante.

        Extrae el texto de los elementos HTML como párrafos y encabezados 
        (p, h1, h2, h3, h4, h5, h6) y los combina en un único texto limpio.

        :param texto: Cadena de texto con contenido HTML.
        :return: Cadena de texto limpio extraído del HTML.
    """
    soup = BeautifulSoup(texto, "html.parser")
    elementos = soup.find_all(["p", "h1", "h2", "h3", "h4", "h5", "h6"])
    fragmentos = [
        elemento.get_text(strip=True)
        for elemento in elementos
        if len(elemento.get_text(strip=True)) > 0
        ]
    return "\n".join(fragmentos)

def limpiar_texto_presegmentacion(texto):
    """
    Realiza una limpieza básica del texto antes de segmentarlo.
    Excluye el paso a minúsculas para no afectar la segmentación basada en títulos.
    """
    # Reemplaza tabulaciones por espacios
    texto = texto.replace("\t", " ")

    # Elimina múltiples espacios consecutivos
    texto = re.sub(r"[ ]{2,}", " ", texto)

    # Normaliza saltos de línea excesivos (más de 2 -> 2)
    texto = re.sub(r"\n{3,}", "\n\n", texto)

    # Reemplaza saltos de línea simples que no separan párrafos por espacio
    texto = re.sub(r"(?<!\n)\n(?!\n)", " ", texto)

    # Elimina caracteres especiales no deseados
    texto = re.sub(r"[^\w\sÁÉÍÓÚÜÑáéíóúüñ.,;:!?()\"'-]", "", texto)

    # Elimina espacios al principio y final
    texto = texto.strip()

    return texto

def limpiar_texto_postsegmentacion(texto):
    """
    Realiza una limpieza avanzada del texto después de la segmentación.
    Incluye el paso a minúsculas y la eliminación de stopwords.
    """
    # Convertir a minúsculas
    texto = texto.lower()

    # Tokenizar y eliminar stopwords
    palabras = word_tokenize(texto)
    palabras_limpias = [palabra for palabra in palabras if palabra not in STOPWORDS]

    # Reconstruir el texto limpio
    return " ".join(palabras_limpias).strip()

# Estrategia 1: Segmentación por saltos de línea
def segmentar_por_saltos(texto):
    """
        Divide el texto en párrafos utilizando saltos de línea.

        La segmentación se realiza considerando:
        - Saltos de línea dobles.
        - Saltos de línea después de un punto seguidos de una mayúscula.

        :param texto: Cadena de texto a segmentar.
        :return: Lista de párrafos segmentados.
    """
    parrafos = re.split(r'\n\s*\n|(?<=\.)\n(?=\s*[A-Z])', texto)
    return [p.strip() for p in parrafos if p.strip()]

# Estrategia 2: Segmentación por títulos
def es_titulo(linea):
    """
    Determina si una línea de texto cumple con los criterios para ser considerada un título.

    Los criterios incluyen:
    - Formato numérico (por ejemplo, "1. Introducción").
    - Formato de letra (por ejemplo, "A. Resumen").
    - Formato de número romano (por ejemplo, "I. Antecedentes").
    - Texto en mayúsculas.
    - Longitud mínima para evitar títulos irrelevantes.
    """
    linea = linea.strip()
    # Filtrar títulos por longitud mínima
    if len(linea) < 5:  # Ajusta el valor según sea necesario
        return False

    # Verificar si coincide con los patrones de títulos
    if TITULO_NUMERICO.match(linea):
        return True
    if TITULO_LETRA.match(linea):
        return True
    match_romano = TITULO_ROMANO.match(linea)
    if match_romano:
        indice = match_romano.group(1)
        if ROMAN_VALID.fullmatch(indice):
            return True
    if TITULO_MAYUSCULAS.match(linea):
        return True

    return False

def segmentar_por_titulo(texto):
    """
        Segmenta el texto en párrafos basándose en títulos detectados.

        La segmentación se realiza identificando líneas que cumplen con los criterios de títulos
        (formato numérico, letra, número romano o texto en mayúsculas). Cada segmento comienza
        con un título y contiene las líneas siguientes hasta el próximo título.

        :param texto: Cadena de texto a segmentar.
        :return: Lista de segmentos de texto, cada uno comenzando con un título.
    """
    lineas = texto.splitlines()
    segmentos = []
    buffer = []
    for linea in lineas:
        if es_titulo(linea):
            if buffer:
                segmentos.append("\n".join(buffer).strip())
                buffer = []
        buffer.append(linea)
    if buffer:
        segmentos.append("\n".join(buffer).strip())
    return segmentos

# Detección de idioma
def detectar_idioma(texto):
    """
        Detecta el idioma de un texto dado.

        Utiliza la biblioteca LangDetect para identificar el idioma del texto.
        Si no se puede detectar el idioma, devuelve "unknown".

        :param texto: Cadena de texto cuyo idioma se desea detectar.
        :return: Código del idioma detectado (por ejemplo, "es" para español) o "unknown".
    """
    try:
        return detect(texto)
    except LangDetectException:
        return "unknown"

# Extracción de títulos
def extraer_titulos(texto):
    """
        Extrae las líneas que cumplen con los criterios para ser consideradas títulos.
    """
    titulos = []
    for linea in texto.splitlines():
        if es_titulo(linea):
            titulos.append(linea.strip())
    return titulos

# Procesamiento principal de archivos
def procesar_archivos():
    """
    Procesa los archivos en el directorio de entrada y realiza la segmentación en párrafos.

    Genera archivos JSON con los párrafos segmentados y un resumen en formato CSV con estadísticas
    del procesamiento.

    :return: None
    """
    print("🚀 Iniciando proceso de segmentación de documentos...")
    resumen = []
    for archivo in os.listdir(PROCESSED_DIR):
        if not archivo.endswith(('.txt', '.html')):
            print(f"⚠️ Archivo no soportado: {archivo}")
            continue

        ruta = os.path.join(PROCESSED_DIR, archivo)
        print(f"ℹ️ Procesando archivo: {archivo}")

        with open(ruta, 'r', encoding='utf-8') as f:
            contenido = f.read()

        if archivo.endswith('.html'):
            contenido = limpiar_html(contenido)

        # Obtener el método, tipo de extracción, tipo original y ID desde la base de datos
        datos_extraccion = obtener_metodo_tipo_extraccion(archivo)
        if not datos_extraccion:
            print(f"⚠️ No se encontraron datos de extracción para el archivo: {archivo}")
            datos_extraccion = {
                "id_fichero": None,
                "metodo_extraccion": "desconocido",
                "tipo_extraccion": "desconocido",
                "tipo_original": "desconocido"
            }

        id_fichero = datos_extraccion["id_fichero"]
        metodo_extraccion = datos_extraccion["metodo_extraccion"]
        tipo_extraccion = datos_extraccion["tipo_extraccion"]
        tipo_original = datos_extraccion["tipo_original"]
        nombre_original = datos_extraccion["nombre_original"]

        for estrategia in ['titulo', 'saltos']:
            print(f"ℹ️ Aplicando estrategia de segmentación: {estrategia}")
            if estrategia == 'titulo':
                parrafos = segmentar_por_titulo(contenido)
            elif estrategia == 'saltos':
                parrafos = segmentar_por_saltos(contenido)
            else:
                continue

            inicio_tiempo = time.time()
            resultado = {
                'archivo_procesado': archivo,
                'id_fichero': id_fichero,
                'tipo_original': tipo_original,
                'nombre_original': nombre_original,
                'parrafos': []
            }

            longitudes = []

            for idx, texto in enumerate(parrafos, 1):
                # Detectar títulos antes de la limpieza postsegmentación
                titulos = extraer_titulos(texto)
                if titulos:
                    print(f"✅ Títulos detectados en párrafo {idx}: {titulos}")

                # Aplicar limpieza postsegmentación después de extraer los títulos
                texto_limpio = limpiar_texto_postsegmentacion(texto)

                idioma = detectar_idioma(texto_limpio)
                resultado['parrafos'].append({
                    'id_parrafo': idx,
                    'texto': texto_limpio,
                    'longitud': len(texto_limpio),
                    'titulos': titulos,
                    'idioma': idioma,
                    'estrategia_segmentacion': estrategia,
                    'metodo_extraccion': metodo_extraccion,
                    'tipo_extraccion': tipo_extraccion,
                    'archivo_procesado': archivo
                })
                longitudes.append(len(texto_limpio))

            fin_tiempo = time.time()
            tiempo_procesado = fin_tiempo - inicio_tiempo

            base_nombre = os.path.splitext(archivo)[0]
            json_path = os.path.join(SEGMENTED_DIR, f"{base_nombre}_{estrategia}.json")
            with open(json_path, 'w', encoding='utf-8') as jf:
                json.dump(resultado, jf, ensure_ascii=False, indent=2)

            print(f"✅ Archivo segmentado y guardado: {json_path}")

            resumen.append({
                'archivo': f"{base_nombre}_{estrategia}",
                'estrategia': estrategia,
                'total_parrafos': len(parrafos),
                'longitud_media': sum(longitudes) / len(longitudes) if longitudes else 0,
                'longitud_minima': min(longitudes) if longitudes else 0,
                'longitud_maxima': max(longitudes) if longitudes else 0,
                'tiempo_procesado_segundos': round(tiempo_procesado, 2),
                'fecha_hora_ejecucion': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                'id_fichero': id_fichero,
                'tipo_original': tipo_original,
                'nombre_original': nombre_original,
                'metodo_extraccion': metodo_extraccion,
                'tipo_extraccion': tipo_extraccion
            })

    resumen_path = os.path.join(SEGMENTED_DIR, 'resumen_segmentacion.csv')

    # Verificar si el archivo ya existe
    if os.path.exists(resumen_path):
        # Leer el archivo existente
        df_existente = pd.read_csv(resumen_path)
        # Concatenar los nuevos registros con los existentes
        df_resumen = pd.concat([df_existente, pd.DataFrame(resumen)], ignore_index=True)
    else:
        # Crear un nuevo DataFrame con las cabeceras y los nuevos registros
        df_resumen = pd.DataFrame(resumen)

    # Guardar el DataFrame actualizado en el archivo CSV
    df_resumen.to_csv(resumen_path, index=False, float_format="%.2f")
    print("✅ Procesamiento completo.")

if __name__ == '__main__':
    procesar_archivos()

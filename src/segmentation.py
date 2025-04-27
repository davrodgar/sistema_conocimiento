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
    Realiza una limpieza básica del texto antes de segmentarlo:
    - Elimina múltiples saltos de línea consecutivos (>2) y los reduce a 2 saltos.
    - Reemplaza saltos de línea simples innecesarios por espacios.
    - Elimina caracteres especiales redundantes (tabs, múltiples espacios).
    - Elimina espacios en blanco al inicio y final.
    """
    # Reemplaza tabulaciones por espacios
    texto = texto.replace("\t", " ")

    # Elimina múltiples espacios consecutivos
    texto = re.sub(r"[ ]{2,}", " ", texto)

    # Normaliza saltos de línea excesivos (más de 2 -> 2)
    texto = re.sub(r"\n{3,}", "\n\n", texto)

    # Reemplaza saltos de línea simples que no separan párrafos por espacio
    texto = re.sub(r"(?<!\n)\n(?!\n)", " ", texto)

    # Elimina espacios al principio y final
    texto = texto.strip()

    return texto

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

        :param linea: Cadena de texto a evaluar.
        :return: True si la línea es un título, False en caso contrario.
    """
    linea = linea.strip()
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

    La función aplica dos estrategias de segmentación:
    - Por títulos detectados en el texto.
    - Por saltos de línea.

    Genera archivos JSON con los párrafos segmentados y un resumen en formato CSV con estadísticas
    del procesamiento.

    :return: None
    """
    resumen = []
    for archivo in os.listdir(PROCESSED_DIR):
        if not archivo.endswith(('.txt', '.html')):
            print(f"[ADVERTENCIA] Archivo no soportado: {archivo}")
            continue

        ruta = os.path.join(PROCESSED_DIR, archivo)
        print(f"[INFO] Procesando archivo: {archivo}")

        with open(ruta, 'r', encoding='utf-8') as f:
            contenido = f.read()

        if archivo.endswith('.html'):
            contenido = limpiar_html(contenido)

        # contenido = limpiar_texto_presegmentacion(contenido)

        for estrategia in ['titulo', 'saltos']:
            if estrategia == 'titulo': # and any(es_titulo(l) for l in contenido.splitlines()):
                parrafos = segmentar_por_titulo(contenido)
            elif estrategia == 'saltos':
                parrafos = segmentar_por_saltos(contenido)
            else:
                continue

            inicio_tiempo = time.time()
            resultado = {
                'archivo_origen': archivo,
                'estrategia': estrategia,
                'parrafos': []
            }

            longitudes = []

            for idx, texto in enumerate(parrafos, 1):
                idioma = detectar_idioma(texto)
                titulos = extraer_titulos(texto)
                if titulos:
                    print(f"[INFO] Títulos detectados en párrafo {idx}: {titulos}")
                resultado['parrafos'].append({
                    'id_parrafo': idx,
                    'texto': texto,
                    'longitud': len(texto),
                    'titulos': titulos,
                    'idioma': idioma
                })
                longitudes.append(len(texto))

            fin_tiempo = time.time()
            tiempo_procesado = fin_tiempo - inicio_tiempo

            base_nombre = os.path.splitext(archivo)[0]
            json_path = os.path.join(SEGMENTED_DIR, f"{base_nombre}_{estrategia}.json")
            with open(json_path, 'w', encoding='utf-8') as jf:
                json.dump(resultado, jf, ensure_ascii=False, indent=2)

            resumen.append({
                'archivo': f"{base_nombre}_{estrategia}",
                'estrategia': estrategia,
                'total_parrafos': len(parrafos),
                'longitud_media': sum(longitudes) / len(longitudes) if longitudes else 0,
                'longitud_minima': min(longitudes) if longitudes else 0,
                'longitud_maxima': max(longitudes) if longitudes else 0,
                'tiempo_procesado_segundos': round(tiempo_procesado, 2),
                'fecha_hora_ejecucion': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            })

    resumen_path = os.path.join(SEGMENTED_DIR, 'resumen_segmentacion.csv')
    if os.path.exists(resumen_path):
        df_existente = pd.read_csv(resumen_path)
        df_resumen = pd.concat([df_existente, pd.DataFrame(resumen)], ignore_index=True)
    else:
        df_resumen = pd.DataFrame(resumen)

    df_resumen.to_csv(resumen_path, index=False, float_format="%.2f")
    print("[INFO] Procesamiento completo.")

if __name__ == '__main__':
    procesar_archivos()

import os
import re
import json
import spacy
import pandas as pd
from langdetect import detect, DetectorFactory
from bs4 import BeautifulSoup

# Configurar langdetect para resultados consistentes
DetectorFactory.seed = 0

# Directorios
PROCESSED_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "../data/processed"))
SEGMENTED_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "../data/segmented"))

# Crear la carpeta de salida si no existe
if not os.path.exists(SEGMENTED_DIR):
    os.makedirs(SEGMENTED_DIR)

# Cargar modelo NER
nlp = spacy.load("es_core_news_sm")

def detectar_titulos(parrafo):
    """
    Detecta títulos dentro de un párrafo.
    """
    lineas = parrafo.split("\n")
    titulos = [linea.strip() for linea in lineas if linea.isupper() or linea.strip().endswith(":") or re.match(r"^\d+[\.\)]", linea.strip())]
    return titulos

def extraer_entidades(parrafo):
    """
    Extrae entidades clave (NER) usando spaCy.
    """
    doc = nlp(parrafo)
    entidades = [
        {"texto": ent.text, "tipo": ent.label_}
        for ent in doc.ents
        if ent.label_ in ["PER", "ORG", "LOC", "MISC", "DATE"]
    ]
    return entidades

def detectar_idioma(parrafo):
    """
    Detecta el idioma de un párrafo usando langdetect.
    """
    try:
        return detect(parrafo)
    except:
        return "unknown"


def segmentar_por_saltos(texto):
    texto = re.sub(r'\n+', '\n', texto)
    parrafos = re.split(r"\n\s*\n|(?<=\.)\n(?=[A-Z])", texto)
    parrafos = [p.strip() for p in parrafos if len(p.strip()) > 30]
    return parrafos

def segmentar_por_longitud(texto, umbral_longitud=400):
    texto = re.sub(r'\n+', '\n', texto)
    fragmentos = re.split(r"\n\s*\n|(?<=\.)\n(?=[A-Z])", texto)
    fragmentos = [f.strip() for f in fragmentos if len(f.strip()) > 0]

    parrafos = []
    buffer = ""
    for fragmento in fragmentos:
        if not buffer:
            buffer = fragmento
        elif len(buffer) + len(fragmento) < umbral_longitud:
            buffer += " " + fragmento
        else:
            parrafos.append(buffer.strip())
            buffer = fragmento
    if buffer:
        parrafos.append(buffer.strip())

    parrafos = [p for p in parrafos if len(p) > 100]
    return parrafos

def segmentar_por_titulo(texto):
    texto = re.sub(r'\n+', '\n', texto)
    lineas = [linea.strip() for linea in texto.split('\n') if linea.strip()]

    segmentos = []
    actual = {"titulo": None, "contenido": []}

    for linea in lineas:
        if linea.isupper() or linea.endswith(":") or re.match(r"^\d+[\.\)]", linea):
            if actual["contenido"]:
                segmentos.append(actual)
            actual = {"titulo": linea, "contenido": []}
        else:
            actual["contenido"].append(linea)

    if actual["contenido"]:
        segmentos.append(actual)

    parrafos = []
    for seg in segmentos:
        texto_unificado = ' '.join(seg["contenido"]).strip()
        if len(texto_unificado) > 100:
            parrafos.append(f"{seg['titulo']}\n{texto_unificado}")
    return parrafos

# Configuración: estrategia de segmentación
ESTRATEGIA = "titulo"  # Opciones: "saltos", "longitud", "titulo"

def segmentar_en_parrafos(texto):
    if ESTRATEGIA == "saltos":
        return segmentar_por_saltos(texto)
    elif ESTRATEGIA == "longitud":
        return segmentar_por_longitud(texto)
    elif ESTRATEGIA == "titulo":
        return segmentar_por_titulo(texto)
    else:
        raise ValueError(f"Estrategia de segmentación desconocida: {ESTRATEGIA}")

def segmentar_en_parrafos(texto):
    """
    Separa el texto en párrafos usando:
    - Dobles saltos de línea
    - Punto seguido de salto de línea y una mayúscula
    """
    texto = re.sub(r'\n+', '\n', texto)  # Normalizar saltos de línea
    parrafos = re.split(r"\n\s*\n|(?<=\.)\n(?=[A-Z])", texto)
    parrafos = [p.strip() for p in parrafos if len(p.strip()) > 30]  # Filtrar fragmentos muy cortos
    return parrafos

def segmentar_html_en_parrafos(html):
    """
    Procesa el contenido HTML y extrae los párrafos y encabezados relevantes.
    """
    soup = BeautifulSoup(html, "html.parser")
    elementos = soup.find_all(["p", "h1", "h2", "h3", "h4", "h5", "h6"])
    parrafos = [elemento.get_text(strip=True) for elemento in elementos if len(elemento.get_text(strip=True)) > 30]
    return parrafos

def procesar_archivos():
    """
    Procesa todos los archivos en la carpeta PROCESSED_DIR,
    aplica el procesamiento adecuado según el tipo de archivo (.txt o .html),
    y guarda los resultados en SEGMENTED_DIR.
    """
    print(f"📂 Carpeta de entrada: {PROCESSED_DIR}")
    for archivo in os.listdir(PROCESSED_DIR):
        print(f"🔍 Archivo encontrado: {archivo}")
        ruta_archivo = os.path.join(PROCESSED_DIR, archivo)
        if archivo.lower().endswith(".txt"):
            print(f"📂 Procesando archivo de texto: {archivo}")
            with open(ruta_archivo, "r", encoding="utf-8") as f:
                contenido = f.read()
            parrafos = segmentar_en_parrafos(contenido)
        elif archivo.lower().endswith(".html"):
            print(f"📂 Procesando archivo HTML: {archivo}")
            with open(ruta_archivo, "r", encoding="utf-8") as f:
                contenido = f.read()
            parrafos = segmentar_html_en_parrafos(contenido)
        else:
            print(f"⚠️ Archivo no soportado: {archivo}")
            continue

        # Procesar cada párrafo para detectar títulos, entidades y el idioma
        resultado = {
            "archivo_origen": archivo,
            "parrafos": []
        }

        for idx, parrafo in enumerate(parrafos, start=1):
            titulos = detectar_titulos(parrafo)
            entidades = extraer_entidades(parrafo)
            idioma = detectar_idioma(parrafo)
            longitud_parrafo = len(parrafo)

            resultado["parrafos"].append({
                "id_parrafo": idx,
                "texto": parrafo,
                "longitud": longitud_parrafo,
                "titulos": titulos,
                "entidades": entidades,
                "idioma": idioma
            })

        # Guardar el resultado en un archivo JSON
        archivo_segmentado = os.path.join(SEGMENTED_DIR, archivo.replace(".txt", "_segmented.json").replace(".html", "_segmented.json"))
        with open(archivo_segmentado, "w", encoding="utf-8") as f:
            json.dump(resultado, f, ensure_ascii=False, indent=4)

        # Traza resumen
        print(f"✅ Archivo segmentado guardado en: {archivo_segmentado}")

        # Traza resumen extendida
        total_parrafos = len(parrafos)
        longitudes = [len(p) for p in parrafos]
        longitud_media = sum(longitudes) / total_parrafos if total_parrafos > 0 else 0
        max_longitud = max(longitudes) if longitudes else 0
        min_longitud = min(longitudes) if longitudes else 0

        print(f"📊 Resumen del archivo {archivo}:")
        print(f"    Total de párrafos procesados: {total_parrafos}")
        print(f"    Longitud media de párrafos: {longitud_media:.2f} caracteres")
        print(f"    Longitud mínima: {min_longitud} caracteres")
        print(f"    Longitud máxima: {max_longitud} caracteres")

        # Guardar resumen en CSV
        resumen_csv_path = os.path.join(SEGMENTED_DIR, "resumen_segmentacion.csv")
        resumen_fila = {
            "archivo": archivo,
            "estrategia": ESTRATEGIA,
            "total_parrafos": total_parrafos,
            "longitud_media": round(longitud_media, 2),
            "longitud_minima": min_longitud,
            "longitud_maxima": max_longitud
        }

        if os.path.exists(resumen_csv_path):
            # Si el archivo CSV ya existe, cargarlo y agregar la nueva fila
            df_resumen = pd.read_csv(resumen_csv_path)
            df_resumen = pd.concat([df_resumen, pd.DataFrame([resumen_fila])], ignore_index=True)
        else:
            # Si el archivo CSV no existe, crear uno nuevo
            df_resumen = pd.DataFrame([resumen_fila])

        # Guardar el DataFrame actualizado en el archivo CSV
        df_resumen.to_csv(resumen_csv_path, index=False, encoding="utf-8")

if __name__ == "__main__":
    procesar_archivos()
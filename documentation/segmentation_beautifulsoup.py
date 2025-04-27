import os
import re
import json
import spacy
from bs4 import BeautifulSoup

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
    Un título es una línea que cumple ciertos criterios, como:
    - Estar en mayúsculas.
    - Terminar con dos puntos (:).
    - Tener un formato de lista (por ejemplo, 1., a)).
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
        if ent.label_ in ["PER", "ORG", "LOC", "MISC", "DATE"]  # Filtrar solo entidades útiles
    ]
    return entidades

def segmentar_html_en_parrafos(html):
    """
    Procesa el contenido HTML y extrae los párrafos y encabezados relevantes.
    """
    soup = BeautifulSoup(html, "html.parser")

    # Extraer párrafos (<p>) y encabezados (<h1>, <h2>, etc.)
    elementos = soup.find_all(["p", "h1", "h2", "h3", "h4", "h5", "h6"])
    parrafos = []

    for elemento in elementos:
        texto = elemento.get_text(strip=True)
        if len(texto) > 30:  # Filtrar fragmentos muy cortos
            parrafos.append(texto)

    return parrafos

def procesar_archivos_json():
    """
    Procesa todos los archivos JSON en la carpeta PROCESSED_DIR,
    extrae el contenido de "X-TIKA:content", lo segmenta en párrafos,
    y guarda los resultados en SEGMENTED_DIR.
    """
    for archivo in os.listdir(PROCESSED_DIR):
        if archivo.endswith(".json"):
            ruta_archivo = os.path.join(PROCESSED_DIR, archivo)
            print(f"📂 Procesando archivo: {archivo}")

            # Leer el contenido del archivo JSON
            with open(ruta_archivo, "r", encoding="utf-8") as f:
                contenido = json.load(f)

            # Extraer el texto del atributo "X-TIKA:content"
            html = contenido.get("X-TIKA:content", "")
            if not html.strip():
                print(f"⚠️ El archivo {archivo} no contiene texto en 'X-TIKA:content'.")
                continue

            # Segmentar el contenido HTML en párrafos
            parrafos = segmentar_html_en_parrafos(html)
            print(f"🔹 Se detectaron {len(parrafos)} párrafos en el archivo {archivo}")

            # Procesar cada párrafo para detectar títulos y entidades NER
            resultado = {
                "archivo_origen": archivo,
                "parrafos": []
            }

            for idx, parrafo in enumerate(parrafos, start=1):
                # Calcular la longitud del párrafo
                longitud_parrafo = len(parrafo)

                # Traza: Mostrar información del párrafo
                print(f"  - Párrafo {idx}: {parrafo[:20]}... (Longitud: {longitud_parrafo})")  # Mostrar los primeros 20 caracteres del párrafo y su longitud

                resultado["parrafos"].append({
                    "id_parrafo": idx,
                    "texto": parrafo,
                    "longitud": longitud_parrafo  # Agregar la longitud del párrafo al JSON
                })

            # Guardar el resultado en un archivo JSON
            archivo_segmentado = os.path.join(SEGMENTED_DIR, archivo.replace(".json", "_segmented.json"))
            with open(archivo_segmentado, "w", encoding="utf-8") as f:
                json.dump(resultado, f, ensure_ascii=False, indent=4)

            print(f"✅ Archivo segmentado guardado en: {archivo_segmentado}")

if __name__ == "__main__":
    procesar_archivos_json()
import os
import re
import json
import spacy

# Directorios
PROCESSED_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "../data/processed"))
SEGMENTED_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "../data/segmented"))

# Crear la carpeta de salida si no existe
if not os.path.exists(SEGMENTED_DIR):
    os.makedirs(SEGMENTED_DIR)

# Cargar modelo NER
nlp = spacy.load("es_core_news_sm")

def extraer_body(texto):
    """
    Extrae el contenido de la etiqueta <body> de un archivo .raw.
    """
    match = re.search(r"<body.*?>(.*?)</body>", texto, re.DOTALL | re.IGNORECASE)
    return match.group(1).strip() if match else ""

def segmentar_en_parrafos(texto):
    """
    Separa el texto en párrafos usando:
    - Dobles saltos de línea
    - Punto seguido de salto de línea y una mayúscula (inicio de un nuevo párrafo)
    """
    texto = re.sub(r'\n+', '\n', texto)  # Normalizar saltos de línea
    parrafos = re.split(r"\n\s*\n|(?<=\.)\n(?=[A-Z])", texto)
    parrafos = [p.strip() for p in parrafos if len(p.strip()) > 30]  # Filtrar fragmentos muy cortos
    return parrafos

def procesar_archivos_raw():
    """
    Procesa todos los archivos .raw en la carpeta PROCESSED_DIR,
    extrae el contenido de la etiqueta <body>, lo segmenta en párrafos,
    y guarda los resultados en SEGMENTED_DIR.
    """
    for archivo in os.listdir(PROCESSED_DIR):
        if archivo.endswith(".raw"):
            ruta_archivo = os.path.join(PROCESSED_DIR, archivo)
            print(f"📂 Procesando archivo: {archivo}")

            # Leer el contenido del archivo .raw
            with open(ruta_archivo, "r", encoding="utf-8") as f:
                contenido = f.read()

            # Extraer el texto de la etiqueta <body>
            texto_body = extraer_body(contenido)
            if not texto_body.strip():
                print(f"⚠️ El archivo {archivo} no contiene texto en la etiqueta <body>.")
                continue

            # Segmentar el texto en párrafos
            parrafos = segmentar_en_parrafos(texto_body)
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
                    "longitud": longitud_parrafo
                })

            # Guardar el resultado en un archivo JSON
            archivo_segmentado = os.path.join(SEGMENTED_DIR, archivo.replace(".raw", "_segmented.json"))
            with open(archivo_segmentado, "w", encoding="utf-8") as f:
                json.dump(resultado, f, ensure_ascii=False, indent=4)

            print(f"✅ Archivo segmentado guardado en: {archivo_segmentado}")

if __name__ == "__main__":
    procesar_archivos_raw()
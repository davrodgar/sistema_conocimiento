"""
Este módulo calcula los embeddings para los párrafos segmentados en archivos JSON.

Funciones principales:
- procesar_archivo: Calcula los embeddings para los párrafos de un archivo JSON.
- procesar_todos_los_json: Procesa todos los archivos JSON en el directorio segmentado.

Utiliza modelos configurables de Sentence Transformers.
"""
import os
import json
from sentence_transformers import SentenceTransformer

# Directorio con los ficheros JSON segmentados
SEGMENTED_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "../data/segmented"))

# Configuración del modelo (puedes cambiar el nombre del modelo aquí)
NOMBRE_MODELO = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"

# Cargar modelo multilingüe que incluye soporte para español
modelo = SentenceTransformer(NOMBRE_MODELO)

def procesar_archivo(ruta_json):
    """
    La función procesar_archivo calcula los embeddings para los párrafos de un archivo JSON. 
    Lee el archivo, genera embeddings para cada párrafo utilizando modelo Sentence Transformers, 
    y guarda los resultados actualizados en el mismo archivo.

    """
    with open(ruta_json, "r", encoding="utf-8") as f:
        datos = json.load(f)

    print(f"[INFO] Calculando embeddings en: {os.path.basename(ruta_json)}")

    for parrafo in datos.get("parrafos", []):
        texto = parrafo.get("texto", "")
        if texto:
            embedding = modelo.encode(texto).tolist()
            parrafo["embedding"] = embedding
            parrafo["modelo_embedding"] = NOMBRE_MODELO

    with open(ruta_json, "w", encoding="utf-8") as f:
        json.dump(datos, f, ensure_ascii=False, indent=2)

def procesar_todos_los_json():
    """
    La función procesar_todos_los_json procesa todos los archivos JSON 
    en el directorio segmentado, calculando los embeddings 
    para los párrafos de cada archivo y actualizando su contenido.

    """
    for archivo in os.listdir(SEGMENTED_DIR):
        if archivo.endswith(".json"):
            ruta = os.path.join(SEGMENTED_DIR, archivo)
            procesar_archivo(ruta)

if __name__ == "__main__":
    print(f"[INFO] Usando el modelo: {NOMBRE_MODELO}")
    procesar_todos_los_json()

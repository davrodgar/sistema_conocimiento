"""
Este módulo calcula los embeddings para los párrafos almacenados en la base de datos.

Funcionalidad principal:
- procesar_parrafos_db: Calcula y almacena los embeddings para los párrafos en la base de datos
  cuyo embedding aún no ha sido generado.

Utiliza modelos configurables de Sentence Transformers.
"""
import os
import json
import time
from tqdm import tqdm
from sentence_transformers import SentenceTransformer

import db_utils  # Módulo utilitario para operaciones con la base de datos

# Configuración del modelo (puedes cambiar el nombre del modelo aquí)
NOMBRE_MODELO = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"

# Cargar modelo multilingüe que incluye soporte para español
modelo = SentenceTransformer(NOMBRE_MODELO)

def procesar_parrafos_db():
    """
    Procesa todos los párrafos en la base de datos cuyo embedding no ha sido calculado.
    Calcula el embedding y lo almacena en la base de datos.
    """
    parrafos = db_utils.obtener_parrafos_sin_embedding()
    total = len(parrafos)
    print(f"[INFO] Párrafos a procesar: {total}")
    if total == 0:
        print("[INFO] No hay párrafos pendientes de vectorizar.")
        return

    start = time.time()
    procesados = 0

    for parrafo in tqdm(parrafos, desc="Calculando embeddings", unit="párrafo"):
        try:
            texto = parrafo["texto"]
            id_parrafo = parrafo["id"]
            if texto:
                embedding = modelo.encode(texto)
                embedding_json = json.dumps(embedding.tolist())
                db_utils.actualizar_embedding_parrafo(id_parrafo, embedding_json, NOMBRE_MODELO)
                procesados += 1
        except Exception as e:
            print(f"❌ Error procesando párrafo ID {parrafo['id']}: {e}")

    elapsed = time.time() - start
    print(f"[INFO] Procesados {procesados} párrafos en {elapsed:.2f} segundos.")

if __name__ == "__main__":
    print(f"[INFO] Usando el modelo: {NOMBRE_MODELO}")
    procesar_parrafos_db()

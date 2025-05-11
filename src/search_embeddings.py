"""
Este módulo busca documentos similares en base a embeddings y genera respuestas utilizando Ollama.

Funciones principales:
- buscar_documentos_similares: Busca documentos relevantes en base a un texto de entrada.
- generar_respuesta_con_ollama: Genera una respuesta en lenguaje natural 
basada en los documentos relevantes.

Requiere:
- Modelo de embeddings de Sentence Transformers.
- API de Ollama para generación de lenguaje natural.
"""

## import os
import json
## import numpy as np
from sentence_transformers import SentenceTransformer
from scipy.spatial.distance import cosine
import ollama
from tqdm import tqdm
from db_utils import obtener_parrafos_para_consulta

# Cargar el modelo de embeddings
embedding_model = SentenceTransformer("sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2")

# Parámetros de filtrado.
UMBRAL_BASE = 0.30
MIN_DOCUMENTOS_RELEVANTES = 1

# Parámetro configurable para el número máximo de párrafos a considerar
NUM_PARRAFOS_A_CONSIDERAR = 5

def cargar_embeddings_desde_archivo(ruta_archivo):
    """Carga los embeddings desde un archivo JSON."""
    with open(ruta_archivo, "r", encoding="utf-8") as f:
        data = json.load(f)

    archivo_procesado = data.get("archivo_procesado", "Archivo desconocido")
    parrafos = data.get("parrafos", [])

    if not parrafos:
        print(f"⚠️ El archivo {ruta_archivo} no contiene párrafos válidos.")
        return archivo_procesado, []

    return archivo_procesado, parrafos

def calcular_similitud(embedding1, embedding2):
    """Calcula la similitud mediante la distancia del coseno."""
    return cosine(embedding1, embedding2)

def buscar_documentos_similares(
    texto,
    filtros_fichero_param=None,
    filtros_parrafo_param=None,
    top_k=NUM_PARRAFOS_A_CONSIDERAR
):
    """
    Busca documentos relevantes en la base de datos SQLite en base a un texto de entrada.
    """
    embedding_texto = embedding_model.encode(texto)
    parrafos_considerados = []

    # Preparar filtros para la consulta
    metodo_extraccion = (
        filtros_fichero_param.get("metodo_extraccion") if filtros_fichero_param else None)
    tipo_extraccion = (
        filtros_fichero_param.get("tipo_extraccion") if filtros_fichero_param else None)
    estrategia_segmentacion = (
        filtros_parrafo_param.get("estrategia_segmentacion") if filtros_parrafo_param else None)
    idioma = filtros_parrafo_param.get("idioma") if filtros_parrafo_param else "es"
    modelo_embedding = (
        filtros_parrafo_param.get("modelo_embedding") if filtros_parrafo_param else None)

    print("🔍 Consultando la base de datos de párrafos...")

    try:
        parrafos_db = obtener_parrafos_para_consulta(
            metodo_extraccion=metodo_extraccion,
            tipo_extraccion=tipo_extraccion,
            estrategia_segmentacion=estrategia_segmentacion,
            idioma=idioma,
            modelo_embedding=modelo_embedding
        )
    except Exception as e:
        print(f"❌ Error al consultar la base de datos: {e}")
        return []

    if not parrafos_db:
        print("⚠️ No se encontraron párrafos en la base de datos con los filtros indicados.")
        return []

    print(f"🔎 Calculando similitud para {len(parrafos_db)} párrafos...")

    for parrafo in tqdm(parrafos_db, desc="Procesando párrafos", unit="párrafo"):
        try:
            embedding_parrafo = parrafo["embedding"]
            if isinstance(embedding_parrafo, str):
                embedding_parrafo = json.loads(embedding_parrafo)
            distancia = calcular_similitud(embedding_texto, embedding_parrafo)
            if distancia <= UMBRAL_BASE:
                parrafos_considerados.append((
                    parrafo.get("nombreOriginal", parrafo.get("archivo_origen", "Desconocido")),
                    distancia,
                    {
                        "id_parrafo": parrafo.get("id_parrafo", "Sin ID"),
                        "texto": parrafo.get("texto", "Texto no disponible")
                    }
                ))
        except Exception as e:
            print(f"⚠️ Error procesando párrafo {parrafo.get('id_parrafo', 'Sin ID')}: {e}")

    # Ordenar y limitar a top_k
    parrafos_considerados = sorted(parrafos_considerados, key=lambda x: x[1])[:top_k]

    if parrafos_considerados:
        print(f"📋 Párrafos relevantes encontrados con el [UMBRAL BASE] = {UMBRAL_BASE}:")
        for archivo, distancia, parrafo in parrafos_considerados:
            id_parrafo = parrafo.get("id_parrafo", "Sin ID")
            print(f"📏 Fichero: {archivo} Párrafo ID: {id_parrafo}, Distancia: {distancia:.4f}")
    else:
        print(f"⚠️ No se encontraron párrafos relevantes con el umbral base ({UMBRAL_BASE}).")
        return []

    return parrafos_considerados

def generar_respuesta_con_ollama(parrafos_considerados, texto_pregunta, modelo_ollama="mistral"):
    """
    Genera una respuesta en lenguaje natural a partir de los párrafos más similares,
    utilizando Ollama como modelo generativo e incluyendo referencias a los documentos originales.
    """
    if not parrafos_considerados:
        return "No se encontró una respuesta clara en los documentos."

    # Construir el prompt para Ollama
    contexto = "A continuación, se presentan extractos de documentos relevantes:\n\n"
    referencias = set()  # Usar un conjunto para evitar duplicados

    for archivo, distancia, parrafo in parrafos_considerados:
        # Extraer el ID del párrafo si está disponible
        parrafo_id = parrafo.get("id_parrafo", "Sin ID")
        texto_parrafo = parrafo.get("texto", "Texto no disponible")

        # Construir el contexto y las referencias con el ID del párrafo
        contexto += f"- [{parrafo_id}] {texto_parrafo}\n\n"
        referencia = (f"{archivo} (distancia: {distancia:.4f})\n"
                    f"Párrafo [{parrafo_id}]: {texto_parrafo}")
        referencias.add(referencia)  # Añadir al conjunto para evitar duplicados

    contexto += f"\nPregunta: {texto_pregunta}\n"
    contexto += "Por favor, genera una respuesta concisa basada en la información proporcionada."

    # Enviar el prompt a Ollama
    respuesta_ollama = ollama.chat(
        model=modelo_ollama,
        messages=[{"role": "user", "content": contexto}]
    )

    # Extraer solo el contenido de la respuesta
    respuesta_generada = respuesta_ollama["message"]["content"]

    # Incluir referencias únicas y párrafos en la salida
    respuesta_final = f"{respuesta_generada}\n\n📌 Ref. utilizadas:\n" + "\n\n".join(referencias)

    return respuesta_final


if __name__ == "__main__":
    TEXTO_PREGUNTA = "¿Qué preserva El sistema de gestión de la seguridad de la información?"

    filtros_fichero = {
        "metodo_extraccion": "PDFPlumber",
        "tipo_extraccion": ".txt"
    }

    filtros_parrafo = {
        "estrategia_segmentacion": "saltos",
        "idioma": "es",
        "modelo_embedding": "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
    }

    documentos_relevantes = buscar_documentos_similares(
        texto=TEXTO_PREGUNTA,
        filtros_fichero_param=filtros_fichero,
        filtros_parrafo_param=filtros_parrafo
    )

    RESPUESTA = generar_respuesta_con_ollama(
        documentos_relevantes, TEXTO_PREGUNTA, modelo_ollama="mistral"
    )

    print("\n🔹 Respuesta generada:")
    print(RESPUESTA)

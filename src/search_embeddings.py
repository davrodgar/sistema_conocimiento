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

import os
import json
import numpy as np
from sentence_transformers import SentenceTransformer
from scipy.spatial.distance import cosine
import ollama  # Asegúrate de que la librería Ollama esté instalada

# Cargar el modelo de embeddings
embedding_model = SentenceTransformer("sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2")

# Parámetros de filtrado.
UMBRAL_BASE = 0.40
UMBRAL_MAXIMO = 0.75
MIN_DOCUMENTOS_RELEVANTES = 1

def cargar_embeddings_desde_archivo(ruta_archivo):
    """Carga los embeddings desde un archivo JSON."""
    with open(ruta_archivo, "r", encoding="utf-8") as f:
        data = json.load(f)
    return data["archivo_procesado"], data["parrafos"]

def calcular_similitud(embedding1, embedding2):
    """Calcula la similitud mediante la distancia del coseno."""
    return cosine(embedding1, embedding2)

def buscar_documentos_similares(texto, ruta_carpeta_embeddings, filtros=None):
    """
    Busca documentos en una carpeta que sean más similares al texto de entrada,
    aplicando filtros opcionales para limitar los segmentos considerados.
    
    Retorna una lista con el nombre del archivo, la menor distancia y el párrafo más similar.
    
    :param texto: Texto de entrada para buscar similitudes.
    :param ruta_carpeta_embeddings: Ruta a la carpeta que contiene los archivos JSON con embeddings.
    :param filtros: Diccionario con los filtros a aplicar. Las claves pueden ser:
        - metodo_extraccion
        - tipo_extraccion
        - estrategia_segmentacion
        - idioma
        - modelo_embedding
    """
    embedding_texto = embedding_model.encode(texto)
    resultados = {}

    print(f"🔍 Procesando carpeta de embeddings: {ruta_carpeta_embeddings}")

    for archivo in os.listdir(ruta_carpeta_embeddings):
        if archivo.endswith(".json"):
            ruta_archivo = os.path.join(ruta_carpeta_embeddings, archivo)
            print(f"📂 Leyendo archivo de embeddings: {archivo}")
            nombre_archivo, parrafos = cargar_embeddings_desde_archivo(ruta_archivo)

            menor_distancia = float("inf")
            parrafo_mas_similar = ""

            for seccion in parrafos:
                # Aplicar filtros
                if filtros:
                    if (filtros.get("metodo_extraccion") and
                        seccion.get("metodo_extraccion") != filtros["metodo_extraccion"]):
                        continue
                    if (filtros.get("tipo_extraccion") and
                        seccion.get("tipo_extraccion") != filtros["tipo_extraccion"]):
                        continue
                    if (filtros.get("estrategia_segmentacion") and
                        seccion.get("estrategia_segmentacion") !=
                                                    filtros["estrategia_segmentacion"]):
                        continue
                    if (filtros.get("idioma") and
                        seccion.get("idioma") != filtros["idioma"]):
                        continue
                    if (filtros.get("modelo_embedding") and
                        seccion.get("modelo_embedding") != filtros["modelo_embedding"]):
                        continue

                # Calcular la distancia del coseno
                embedding_parrafo = np.array(seccion["embedding"])
                distancia = calcular_similitud(embedding_texto, embedding_parrafo)

                if distancia < menor_distancia:
                    menor_distancia = distancia
                    parrafo_mas_similar = seccion["texto"]

            if menor_distancia < float("inf"):
                print(f"✅ Archivo procesado: {archivo}, menor distancia: {menor_distancia:.4f}")
                resultados[nombre_archivo] = (menor_distancia, parrafo_mas_similar)

    resultados_ordenados = sorted(resultados.items(), key=lambda x: x[1][0])

    umbral_actual = UMBRAL_BASE
    documentos_filtrados = [
        (archivo, distancia, parrafo)
        for archivo, (distancia, parrafo)
        in resultados_ordenados if distancia <= umbral_actual
    ]

    # Si no se encuentran documentos con el primer umbral, intentar con el segundo
    if len(documentos_filtrados) < MIN_DOCUMENTOS_RELEVANTES:
        print(f"⚠️ No se encontraron documentos relevantes con el umbral base ({UMBRAL_BASE}). Intentando con el umbral máximo ({UMBRAL_MAXIMO}).")
        umbral_actual = UMBRAL_MAXIMO
        documentos_filtrados = [
            (archivo, distancia, parrafo)
            for archivo, (distancia, parrafo)
            in resultados_ordenados if distancia <= umbral_actual
        ]

    # Si aún no se encuentran documentos, mostrar mensaje final
    if len(documentos_filtrados) < MIN_DOCUMENTOS_RELEVANTES:
        print("⚠️ No se encontraron documentos relevantes con los umbrales establecidos.")
        return []

    print(f"📋 Documentos relevantes encontrados: {len(documentos_filtrados)}")
    return documentos_filtrados

def generar_respuesta_con_ollama(texto_pregunta, ruta_carpeta_embeddings, modelo_ollama="mistral"):
    """
    Genera una respuesta en lenguaje natural a partir de los párrafos más similares,
    utilizando Ollama como modelo generativo e incluyendo referencias a los documentos originales.
    """
    documentos_encontrados = buscar_documentos_similares(texto_pregunta, ruta_carpeta_embeddings)

    if not documentos_encontrados:
        return "No se encontró una respuesta clara en los documentos."

    # Construir el prompt para Ollama
    contexto = "A continuación, se presentan extractos de documentos relevantes:\n\n"
    referencias = []

    for archivo, distancia, parrafo in documentos_encontrados[:3]:
        # Tomar hasta 3 párrafos relevantes
        contexto += f"- {parrafo}\n\n"
        referencias.append(f"{archivo} (distancia: {distancia:.4f})\nPárrafo: {parrafo}")

    contexto += f"\nPregunta: {texto_pregunta}\n"
    contexto += "Por favor, genera una respuesta concisa basada en la información proporcionada."

    # Enviar el prompt a Ollama
    respuesta_ollama = ollama.chat(
                                    model=modelo_ollama,
                                    messages=[{"role": "user", "content": contexto}]
                                    )

    # Extraer solo el contenido de la respuesta
    respuesta_generada = respuesta_ollama["message"]["content"]

    # Incluir referencias y párrafos en la salida
    respuesta_final = f"{respuesta_generada}\n\n📌 Ref. utilizadas:\n" + "\n\n".join(referencias)

    return respuesta_final

if __name__ == "__main__":
    # Ejemplo de uso
    carpeta_embeddings = os.path.abspath(os.path.join(os.path.dirname(__file__), "../data"))
    # Verificar si la carpeta existe
    if not os.path.exists(carpeta_embeddings):
        raise FileNotFoundError(f"La carpeta de embeddings no existe: {carpeta_embeddings}")

    TEXTO_PREGUNTA = "¿Qué preserva El sistema de gestión de la seguridad de la información?"

    filtros_consulta = {
        "metodo_extraccion": "PDFPlumber",
        "tipo_extraccion": ".txt",
        "estrategia_segmentacion": "titulo",
        "idioma": "es",
        "modelo_embedding": "paraphrase-multilingual-MiniLM-L12-v2"
    }

    documentos_relevantes = buscar_documentos_similares(
        texto="¿Qué preserva El sistema de gestión de la seguridad de la información?",
        ruta_carpeta_embeddings=carpeta_embeddings,  # Usar la variable correctamente
        filtros=filtros_consulta
    )

    RESPUESTA = generar_respuesta_con_ollama(
        TEXTO_PREGUNTA, carpeta_embeddings, modelo_ollama="mistral")

    # Mostrar la respuesta generada
    print("\n🔹 Respuesta generada:")
    print(RESPUESTA)

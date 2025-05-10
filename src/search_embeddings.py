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
import ollama

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

def buscar_documentos_similares(texto, ruta_carpeta_embeddings,
                                 filtros_fichero_param=None, filtros_parrafo_param=None):
    """
    Busca documentos relevantes en una carpeta de embeddings en base a un texto de entrada.
    """
    embedding_texto = embedding_model.encode(texto)
    parrafos_considerados = []  # Renombrado a snake_case

    print(f"🔍 Procesando carpeta de embeddings: {ruta_carpeta_embeddings}")

    for archivo in os.listdir(ruta_carpeta_embeddings):
        if archivo.endswith(".json"):
            ruta_archivo = os.path.join(ruta_carpeta_embeddings, archivo)
            print(f"📂 Leyendo archivo de embeddings: {archivo}")
            nombre_archivo, parrafos = cargar_embeddings_desde_archivo(ruta_archivo)

            # Filtrado a nivel de fichero
            if filtros_fichero_param:
                if (filtros_fichero_param.get("metodo_extraccion") and
                    parrafos and parrafos[0].get("metodo_extraccion") !=
                        filtros_fichero_param["metodo_extraccion"]):
                    print(f"❌ Archivo {archivo} descartado por 'metodo_extraccion'.")
                    continue
                if (filtros_fichero_param.get("tipo_extraccion") and
                    parrafos and parrafos[0].get("tipo_extraccion") !=
                        filtros_fichero_param["tipo_extraccion"]):
                    print(f"❌ Archivo {archivo} descartado por 'tipo_extraccion'.")
                    continue
                if (filtros_fichero_param.get("estrategia_segmentacion") and
                    parrafos and parrafos[0].get("estrategia_segmentacion") !=
                        filtros_fichero_param["estrategia_segmentacion"]):
                    print(f"❌ Archivo {archivo} descartado por 'estrategia_segmentacion'.")
                    continue

            # Procesar párrafos si el fichero cumple los filtros
            for seccion in parrafos:
                if filtros_parrafo_param:
                    if (filtros_parrafo_param.get("estrategia_segmentacion") and
                        seccion.get("estrategia_segmentacion") !=
                         filtros_parrafo_param["estrategia_segmentacion"]):
                        print(f"⚠️ Párrafo descartado por 'estrategia_segmentacion'. "
                              f"Valor en fichero: {seccion.get('estrategia_segmentacion')}, "
                              f"Valor esperado: {filtros_parrafo_param['estrategia_segmentacion']}")
                        continue
                    if (filtros_parrafo_param.get("idioma") and
                        seccion.get("idioma") != filtros_parrafo_param["idioma"]):
                        print(f"⚠️ Párrafo descartado por 'idioma'. "
                              f"Valor en fichero: {seccion.get('idioma')}, "
                              f"Valor esperado: {filtros_parrafo_param['idioma']}")
                        continue
                    if (filtros_parrafo_param.get("modelo_embedding") and
                        seccion.get("modelo_embedding").split("/")[-1] !=
                         filtros_parrafo_param["modelo_embedding"].split("/")[-1]):
                        print(f"⚠️ Párrafo descartado por 'modelo_embedding'. "
                              f"Valor en fichero: {seccion.get('modelo_embedding')}, "
                              f"Valor esperado: {filtros_parrafo_param['modelo_embedding']}")
                        continue

                # Verificar si el embedding existe
                if "embedding" not in seccion:
                    print(f"⚠️ El párrafo con ID {seccion.get('id_parrafo', 'Sin ID')} "
                          f"no tiene un embedding válido.")
                    continue

                # Calcular la distancia del coseno
                embedding_parrafo = np.array(seccion["embedding"])
                distancia = calcular_similitud(embedding_texto, embedding_parrafo)

                # Extraer el ID del párrafo
                id_parrafo = seccion.get("id_parrafo", "Sin ID")

                # Imprimir solo los párrafos que cumplen con el umbral actual
                if distancia <= UMBRAL_BASE:
                    print(f"📏 Párrafo ID: {id_parrafo}, Distancia: {distancia:.4f}")
                    parrafos_considerados.append((archivo, distancia, seccion))

    # Ordenar los párrafos considerados por distancia y limitar a NUM_PARRAFOS_A_CONSIDERAR
    parrafos_considerados = sorted(parrafos_considerados, key=lambda x: x[1]
                                   )[:NUM_PARRAFOS_A_CONSIDERAR]

    if len(parrafos_considerados) > 0:
        print(f"📋 Párrafos relevantes encontrados con el umbral base ({UMBRAL_BASE}):")
        for archivo, distancia, parrafo in parrafos_considerados:
            id_parrafo = parrafo.get("id_parrafo", "Sin ID")
            print(f"📏 [UMBRAL BASE] Párrafo ID: {id_parrafo}, Distancia: {distancia:.4f}")
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
    carpeta_embeddings = os.path.abspath(os.path.join(os.path.dirname(__file__), "../data"))
    if not os.path.exists(carpeta_embeddings):
        raise FileNotFoundError(f"La carpeta de embeddings no existe: {carpeta_embeddings}")

    TEXTO_PREGUNTA = "¿Qué preserva El sistema de gestión de la seguridad de la información?"

    filtros_fichero = {
        "metodo_extraccion": "PDFPlumber",
        "tipo_extraccion": ".txt"
    }

    filtros_parrafo = {
        "estrategia_segmentacion": "saltos",
        "idioma": "es",
        "modelo_embedding": "paraphrase-multilingual-MiniLM-L12-v2"
    }

    # Llamar a buscar_documentos_similares una sola vez
    documentos_relevantes = buscar_documentos_similares(
        texto=TEXTO_PREGUNTA,
        ruta_carpeta_embeddings=carpeta_embeddings,
        filtros_fichero_param=filtros_fichero,
        filtros_parrafo_param=filtros_parrafo
    )

    # Pasar los resultados a generar_respuesta_con_ollama
    RESPUESTA = generar_respuesta_con_ollama(
        documentos_relevantes, TEXTO_PREGUNTA, modelo_ollama="mistral"
    )

    # Mostrar la respuesta generada
    print("\n🔹 Respuesta generada:")
    print(RESPUESTA)

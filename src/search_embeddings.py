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
import time
import json
from sentence_transformers import SentenceTransformer
from scipy.spatial.distance import cosine
import ollama
from tqdm import tqdm
from db_utils import obtener_parrafos_para_consulta,registrar_consulta,registrar_fragmentos_consulta


# Configuración del modelo (puedes cambiar el nombre del modelo aquí)
NOMBRE_MODELO_EMBEDDING = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"

# Cargar modelo multilingüe con soporte para español
embedding_model = SentenceTransformer(NOMBRE_MODELO_EMBEDDING)

# Umbral para considerar un párrafo relevante (distancia del coseno)
UMBRAL_BASE = 0.30

# Número máximo de párrafos a considerar
NUM_PARRAFOS_A_CONSIDERAR = 5

def calcular_similitud(embedding1, embedding2):
    """Calcula la distancia del coseno entre dos embeddings."""
    return cosine(embedding1, embedding2)

def buscar_documentos_similares(
    texto,
    filtros_fichero_param=None,
    filtros_parrafo_param=None,
    top_k=NUM_PARRAFOS_A_CONSIDERAR
):
    """
    Busca documentos relevantes en la base de datos SQLite en base a un texto de entrada.
    Devuelve una lista de tuplas con (archivo, distancia, info_parrafo), 
    el número de párrafos considerados y el tiempo empleado.
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
        return [], 0, 0.0

    if not parrafos_db:
        print("⚠️ No se encontraron párrafos en la base de datos con los filtros indicados.")
        return [], 0, 0.0

    print(f"🔎 Calculando similitud para {len(parrafos_db)} párrafos...")

    t0 = time.time()
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
                        "id_fichero": parrafo.get("id_fichero"),
                        "id_parrafo": parrafo.get("id_parrafo", "Sin ID"),
                        "texto": parrafo.get("texto", "Texto no disponible")
                    }
                ))
        except Exception as e:
            print(f"⚠️ Error procesando párrafo {parrafo.get('id_parrafo', 'Sin ID')}: {e}")
    t1 = time.time()
    tiempo_top_k = t1 - t0

    # Ordenar y limitar a top_k
    parrafos_considerados = sorted(parrafos_considerados, key=lambda x: x[1])[:top_k]

    if parrafos_considerados:
        print(f"📋 Párrafos relevantes encontrados con el [UMBRAL BASE] = {UMBRAL_BASE}:")
        for archivo, distancia, parrafo in parrafos_considerados:
            id_parrafo = parrafo.get("id_parrafo", "Sin ID")
            print(f"📏 Fichero: {archivo} Párrafo ID: {id_parrafo}, Distancia: {distancia:.4f}")
    else:
        print(f"⚠️ No se encontraron párrafos relevantes con el umbral base ({UMBRAL_BASE}).")
        return [], len(parrafos_db), tiempo_top_k

    return parrafos_considerados, len(parrafos_db), tiempo_top_k

def generar_respuesta_con_ollama(parrafos_considerados, texto_pregunta, modelo_ollama="mistral"):
    """
    Genera una respuesta en lenguaje natural a partir de los párrafos más similares,
    utilizando Ollama como modelo generativo e incluyendo referencias a los documentos originales.
    Devuelve la respuesta y el tiempo empleado.
    """
    if not parrafos_considerados:
        return "No se encontró una respuesta clara en los documentos.", 0.0

    # Construir el prompt para Ollama
    contexto = "A continuación, se presentan extractos de documentos relevantes:\n\n"
    referencias = set()  # Usar un conjunto para evitar duplicados

    for archivo, distancia, parrafo in parrafos_considerados:
        parrafo_id = parrafo.get("id_parrafo", "Sin ID")
        texto_parrafo = parrafo.get("texto", "Texto no disponible")
        contexto += f"- [{parrafo_id}] {texto_parrafo}\n\n"
        referencia = (f"{archivo} (distancia: {distancia:.4f})\n"
                      f"Párrafo [{parrafo_id}]: {texto_parrafo}")
        referencias.add(referencia)

    contexto += f"\nPregunta: {texto_pregunta}\n"
    contexto += "Por favor, genera una respuesta concisa basada en la información proporcionada."

    t0 = time.time()
    respuesta_ollama = ollama.chat(
        model=modelo_ollama,
        messages=[{"role": "user", "content": contexto}]
    )
    t1 = time.time()
    tiempo_llm = t1 - t0

    respuesta_generada = respuesta_ollama["message"]["content"]
    respuesta_final = f"{respuesta_generada}\n\n📌 Ref. utilizadas:\n" + "\n\n".join(referencias)

    return respuesta_final, tiempo_llm

def ejecutar_consulta_semantica(consulta, modelo_ollama="mistral"):
    """
    Ejecuta una consulta semántica completa: busca documentos similares y genera una respuesta.
    Registra la consulta y los fragmentos utilizados en la base de datos.
    """
    pregunta = consulta.get("pregunta")
    config = consulta.get("config", {})

    filtros_fichero_param = config.get("filtros_fichero_param")
    filtros_parrafo_param = config.get("filtros_parrafo_param")

    # Buscar documentos relevantes
    documentos_relevantes, num_parrafos_considerados, tiempo_top_k = buscar_documentos_similares(
        texto=pregunta,
        filtros_fichero_param=filtros_fichero_param,
        filtros_parrafo_param=filtros_parrafo_param
    )

    # Generar respuesta con Ollama
    respuesta, tiempo_llm = generar_respuesta_con_ollama(
        documentos_relevantes, pregunta, modelo_ollama=modelo_ollama
    )

    # Registrar la consulta y los fragmentos utilizados
    id_consulta = registrar_consulta(
        pregunta,
        NOMBRE_MODELO_EMBEDDING,
        modelo_ollama,
        respuesta,
        umbral_base=UMBRAL_BASE,
        top_k=NUM_PARRAFOS_A_CONSIDERAR,
        num_parrafos_considerados=num_parrafos_considerados,
        tiempo_top_k=tiempo_top_k,
        tiempo_llm=tiempo_llm,
        filtros_fichero_param=filtros_fichero_param,
        filtros_parrafo_param=filtros_parrafo_param
    )

    fragmentos_para_registro = [
        {
            "id_fichero": parrafo["id_fichero"],
            "id_parrafo": parrafo["id_parrafo"],
            "distancia": distancia
        }
        for _, distancia, parrafo in documentos_relevantes
    ]

    if id_consulta:
        registrar_fragmentos_consulta(
            id_consulta,
            fragmentos_para_registro
        )
        print(f"[INFO] Consulta y fragmentos registrados en la base de datos "
               f"(id_consulta={id_consulta})")
    else:
        print("❌ No se pudo registrar la consulta en la base de datos.")

    return respuesta

if __name__ == "__main__":
    # Definir la consulta en el mismo formato que en evaluacion_recuperacionsemantica.py
    consultas = [
        {
            "pregunta": "¿Qué preserva el sistema de gestión de la seguridad de la información?",
            "config": {
                "filtros_fichero_param": {
                    "metodo_extraccion": "PDFPlumber",
                    "tipo_extraccion": ".txt"
                },
                "filtros_parrafo_param": {
                    "estrategia_segmentacion": "saltos",
                    "idioma": "es",
                    "modelo_embedding": "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
                }
            }
        }
    ]

    # Ejecutar la consulta usando la nueva función
    for consulta_item in consultas:
        respuesta_consulta = ejecutar_consulta_semantica(consulta_item, modelo_ollama="mistral")
        print("\n🔹 Respuesta generada:")
        print(respuesta_consulta)

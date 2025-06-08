"""
Script para evaluar la recuperación semántica de preguntas sobre documentos 
usando embeddings y Ollama.
"""
import json
from search_embeddings import ejecutar_consulta_semantica


# Lista de preguntas y configuraciones
consultas = [
    {
        "pregunta": "¿Cuales son los distintos tipos de ofertas que se gestionan habitualmente?",
        "config": {
            "filtros_fichero_param": {
                "metodo_extraccion": "PDFPlumber",
                "tipo_extraccion": ".txt"
            },
            "filtros_parrafo_param": {
                "estrategia_segmentacion": "titulo",
                "idioma": "es",
                "modelo_embedding": "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
            }
        }
    },
    {
        "pregunta": "¿Cuales son los distintos tipos de ofertas que se gestionan habitualmente?",
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
    },
    {
        "pregunta": "¿Cuales son los distintos tipos de ofertas que se gestionan habitualmente?",
        "config": {
            "filtros_fichero_param": {
                "metodo_extraccion": "TIKA_application_json",
                "tipo_extraccion": ".html"
            },
            "filtros_parrafo_param": {
                "estrategia_segmentacion": "titulo",
                "idioma": "es",
                "modelo_embedding": "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
            }
        }
    },
    {
        "pregunta": "¿Cuales son los distintos tipos de ofertas que se gestionan habitualmente?",
        "config": {
            "filtros_fichero_param": {
                "metodo_extraccion": "TIKA_application_json",
                "tipo_extraccion": ".html"
            },
            "filtros_parrafo_param": {
                "estrategia_segmentacion": "saltos",
                "idioma": "es",
                "modelo_embedding": "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
            }
        }
    },
    {
        "pregunta": "¿Cuales son los distintos tipos de ofertas que se gestionan habitualmente?",
        "config": {
            "filtros_fichero_param": {
                "metodo_extraccion": "TIKA_text_plain",
                "tipo_extraccion": ".txt"
            },
            "filtros_parrafo_param": {
                "estrategia_segmentacion": "titulo",
                "idioma": "es",
                "modelo_embedding": "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
            }
        }
    },
    {
        "pregunta": "¿Cuales son los distintos tipos de ofertas que se gestionan habitualmente?",
        "config": {
            "filtros_fichero_param": {
                "metodo_extraccion": "TIKA_text_plain",
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

for consulta in consultas:
    pregunta = consulta["pregunta"]
    print(f"\n🔍 Ejecutando consulta: {pregunta}")
    print("🔧 Configuración de la consulta:")
    print(json.dumps(consulta["config"], indent=4, ensure_ascii=False))
    respuesta = ejecutar_consulta_semantica(consulta, modelo_ollama="mistral")
    print("\n🔹 Respuesta generada:")
    print(respuesta)

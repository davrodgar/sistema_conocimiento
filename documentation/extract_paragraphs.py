import os
import json
import re

# Ruta al archivo JSON extraído por Apache Tika
ruta_json = r"c:\Users\arodri\Proyectos\TFM_2025\sistema_conocimiento\data\processed\ATN_Q_L2_03 Ed 10 Ofertas y Rev Contrato Offers and Contract Rev.doc_TIKAextraction.json"

# Función para segmentar texto en párrafos
def segmentar_en_parrafos(texto):
    """
    Separa el texto en párrafos usando:
    - Dobles saltos de línea
    - Punto seguido de salto de línea y una mayúscula (inicio de un nuevo párrafo)
    """
    # Normalizar saltos de línea
    texto = re.sub(r'\n+', '\n', texto)  # Reemplazar múltiples saltos de línea por uno solo

    # Separar por dobles saltos de línea o punto seguido de un salto de línea y mayúscula
    parrafos = re.split(r"\n\s*\n|(?<=\.)\n(?=[A-Z])", texto)

    # Filtrar fragmentos muy cortos
    parrafos = [p.strip() for p in parrafos if len(p.strip()) > 30]

    return parrafos

# Leer el archivo JSON
def extraer_parrafos_desde_json(ruta_json):
    try:
        with open(ruta_json, "r", encoding="utf-8") as f:
            contenido = json.load(f)

        # Extraer el contenido de "X-TIKA:content"
        texto = contenido.get("X-TIKA:content", "")
        if not texto.strip():
            print("⚠️ No se encontró contenido en 'X-TIKA:content'.")
            return []

        # Segmentar el texto en párrafos
        parrafos = segmentar_en_parrafos(texto)
        print(f"🔹 Se detectaron {len(parrafos)} párrafos.")
        return parrafos

    except Exception as e:
        print(f"❌ Error al procesar el archivo JSON: {e}")
        return []

# Guardar los párrafos en un archivo JSON con identificadores
def guardar_parrafos_en_json(parrafos, ruta_salida):
    try:
        # Crear una lista de diccionarios con id y texto
        parrafos_con_ids = [{"id": idx + 1, "texto": parrafo} for idx, parrafo in enumerate(parrafos)]

        with open(ruta_salida, "w", encoding="utf-8") as f:
            json.dump({"parrafos": parrafos_con_ids}, f, ensure_ascii=False, indent=4)
        print(f"✅ Párrafos guardados en: {ruta_salida}")
    except Exception as e:
        print(f"❌ Error al guardar los párrafos: {e}")

if __name__ == "__main__":
    # Extraer párrafos desde el archivo JSON
    parrafos = extraer_parrafos_desde_json(ruta_json)

    # Guardar los párrafos en un archivo JSON
    if parrafos:
        ruta_salida = r"c:\Users\arodri\Proyectos\TFM_2025\sistema_conocimiento\data\segmented\parrafos_extraidos.json"
        os.makedirs(os.path.dirname(ruta_salida), exist_ok=True)
        guardar_parrafos_en_json(parrafos, ruta_salida)
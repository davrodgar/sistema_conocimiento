# Sistema de Conocimiento para Documentos Empresariales

Este proyecto forma parte del Trabajo Fin de Máster (TFM)  
del Máster de Ingeniería del Software de la Universidad de Sevilla.  
Su objetivo es desarrollar un sistema modular que procese documentos de texto en diferentes formatos, extraiga conocimiento relevante, lo almacene de forma estructurada y permita su consulta en lenguaje natural de manera local, sin dependencias externas.

---

## Estructura del sistema

1. **Ingesta de Documentos**  
   Detecta archivos nuevos en la carpeta `data/input/`, extrae su contenido mediante herramientas especializadas (Apache Tika, pdfplumber, python-docx, etc.) y registra todo en una base de datos SQLite.

2. **Procesamiento del Conocimiento**  
   Limpia, segmenta y vectoriza el contenido textual en fragmentos semánticos, utilizando el modelo `MiniLM-L12-v2` para generar embeddings.

3. **Almacenamiento**  
   Utiliza SQLite para registrar los documentos, fragmentos, vectores y consultas, garantizando trazabilidad completa.

4. **Consulta en Lenguaje Natural**  
   Implementa un flujo de RAG (Retrieval-Augmented Generation) que permite realizar preguntas en lenguaje natural y obtener respuestas contextualizadas, usando el modelo `Mistral 7B` ejecutado localmente mediante Ollama.

5. **Evaluación y Validación**  
   Incluye scripts para validar automáticamente la calidad del contenido extraído, la segmentación y la recuperación semántica.

---

## 🛠 Requisitos

- Python 3.9 o superior
- Java (para ejecutar Apache Tika Server)
- Apache Tika server (`tika-server-standard.jar`) en `src/tools/`
- Ollama instalado localmente (`ollama run mistral`)
- Microsoft Word (solo necesario si se desea extraer contenido desde archivos `.doc`)
- Virtualenv (opcional pero recomendado)

---

## ▶️ Instalación

```bash
# Clonar el repositorio
git clone https://github.com/davrodgar/sistema_conocimiento.git
cd sistema_conocimiento

# Crear y activar el entorno virtual
python -m venv venv_TFM2025
# En Windows
venv_TFM2025\Scripts\activate
# En macOS/Linux
source venv_TFM2025/bin/activate

# Instalar las dependencias
pip install --upgrade pip
pip install -r requirements.txt
```

---

## 🚀 Uso rápido

1. **Preparar los documentos**  
   Coloca los archivos a procesar en la carpeta `data/input/`.

2. **Ejecutar la ingesta y procesamiento**  
   Lanza los scripts principales desde la carpeta `src/` para extraer, segmentar y vectorizar los documentos.

   ```bash
   python src/ingesta_documentos.py
   python src/procesamiento_conocimiento.py
   ```

3. **Realizar consultas en lenguaje natural**  
   Ejecuta el script de recuperación semántica:

   ```bash
   python src/evaluacion_recuperacionsemantica.py
   ```

4. **Evaluar resultados**  
   Usa los scripts de evaluación para validar la segmentación y la recuperación:

   ```bash
   python src/evaluacion_segmentacion.py
   ```

---

## 📂 Estructura de carpetas

```
sistema_conocimiento/
│
├── data/
│   ├── input/           # Documentos originales
│   ├── output/          # Resultados y fragmentos procesados
│   └── embeddings/      # Vectores generados
│
├── src/
│   ├── ingesta_documentos.py
│   ├── procesamiento_conocimiento.py
│   ├── evaluacion_segmentacion.py
│   ├── evaluacion_recuperacionsemantica.py
│   └── ...
│
├── requirements.txt
└── readme.md
```

---

## 📝 Notas

- El sistema está pensado para ejecutarse completamente en local, sin enviar datos a servicios externos.
- Se recomienda mantener actualizado el archivo `requirements.txt` usando `pip freeze > requirements.txt` tras instalar o actualizar paquetes.
- Para dudas o mejoras, abre un issue en el repositorio.

---

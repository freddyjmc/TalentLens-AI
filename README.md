# TalentLens AI

Asistente de búsqueda de empleo con IA. Ayuda a analizar ofertas, revisar tu CV, practicar entrevistas y guardar todo en una base de datos, desde una sola aplicación web.

> Proyecto desarrollado durante el bootcamp de IA de F5.

<!-- TODO: añade aquí una captura de pantalla o un GIF de la app -->
<!-- ![TalentLens AI](docs/captura.png) -->

## Qué hace

| Sección | Descripción |
|---|---|
| **Analizar ofertas** | Sube la oferta en texto o PDF, o pega un enlace, y obtén el puesto, la empresa, la ubicación, las habilidades requeridas, palabras clave y un resumen. |
| **Revisar CV** | Sube tu CV en texto o PDF y recibe una valoración sobre si pasaría filtros ATS, con sugerencias de mejora. |
| **CV optimizado para ATS** | Genera una versión de tu CV preparada para filtros ATS (opcionalmente para un puesto concreto) y descárgala en PDF, Word o TXT. No inventa datos: lo que falta queda marcado como `[COMPLETAR]`. Un verificador revisa el resultado antes de descargarlo. |
| **Buscar empleo** | A partir de tu CV (el optimizado, uno guardado o uno que subas en texto, PDF o Word), la IA propone los puestos a buscar, consulta ofertas reales en la API de Adzuna y puntúa de 0 a 100 cuánto encaja cada una, explicando por qué. Cada oferta enlaza primero a la web de la empresa y después al anuncio. |
| **Mis candidaturas** | Panel de seguimiento por CV: marca una oferta como postulada y sigue su estado (Postulada, Vista, Entrevista, Descartada, Aceptada) con notas. También puedes añadir candidaturas a mano. La inscripción siempre la haces tú. |
| **Practicar entrevistas** | Indica un rol y genera preguntas habituales de entrevista. |
| **Asistente inteligente** | Chat con un asistente especializado en empleo, CVs y desarrollo profesional. |
| **Datos guardados** | Consulta las ofertas, revisiones de CV y CVs optimizados guardados en MongoDB y descárgalos en CSV. |

## Tecnologías

- **Python 3.9+**
- **Streamlit**: interfaz web
- **OpenAI API** (`gpt-4o-mini`): análisis, revisión y chat
- **MongoDB** con **PyMongo**: almacenamiento
- **Adzuna API**: búsqueda de ofertas de empleo reales
- **Requests** y **lxml**: lectura de ofertas desde un enlace (con **Selenium** como respaldo para páginas que necesitan JavaScript)
- **pypdf**: lectura de PDF
- **python-docx** y **fpdf2**: exportación del CV a Word y PDF
- **Pandas**: tablas y exportación a CSV
- **Docker Compose**: base de datos MongoDB

## Instalación

### 1. Clonar el repositorio

```bash
git clone https://github.com/freddyjmc/TalentLens-AI.git
cd TalentLens-AI
```

### 2. Crear el entorno e instalar dependencias

```bash
python -m venv venv
venv\Scripts\activate        # Windows
# source venv/bin/activate   # Linux / macOS
pip install -r requirements.txt
```

### 3. Configurar variables de entorno

Copia `.env.example` como `.env` y completa tu clave de OpenAI:

```bash
copy .env.example .env       # Windows
# cp .env.example .env       # Linux / macOS
```

| Variable | Para qué sirve |
|---|---|
| `OPENAI_API_KEY` | Clave de la API de OpenAI |
| `MONGODB_URI` | Dirección de MongoDB (en local, `mongodb://localhost:27017/`) |
| `MONGODB_DB_NAME` | Nombre de la base de datos (en `.env.example`, `asistente`) |
| `OPENAI_MODEL` | Opcional. Modelo de OpenAI (por defecto `gpt-4o-mini`) |
| `ADZUNA_APP_ID` / `ADZUNA_APP_KEY` | Credenciales gratuitas de [Adzuna](https://developer.adzuna.com/) para «Buscar empleo» |

### 4. Arrancar MongoDB

```bash
docker compose up -d mongodb
```

### 5. Ejecutar la aplicación

```bash
streamlit run app.py
```

Se abrirá en <http://localhost:8501>.

> **Nota:** la lectura de ofertas desde un enlace funciona sin navegador, también dentro de Docker. Solo las páginas que necesitan JavaScript usan Selenium, que requiere Google Chrome instalado (en local). Algunas webs bloquean la lectura automática: en ese caso la app lo indica y puedes subir el texto de la oferta como archivo.

## Estructura del proyecto

```
TalentLens-AI/
├── app.py               # Interfaz de Streamlit
├── db_manager.py        # Conexión y operaciones con MongoDB
├── cv_reviewer.py       # Revisión de CV con OpenAI
├── cv_generator.py      # Generación del CV optimizado para ATS
├── cv_export.py         # Exportación del CV a PDF, Word y TXT
├── cv_verifier.py       # Verificación del CV generado (reglas + segunda revisión con IA)
├── job_search.py        # Búsqueda de ofertas en Adzuna y puntuación con IA
├── offer_analysis.py    # Análisis de ofertas con OpenAI
├── offer_scraper.py     # Lectura de ofertas desde un enlace
├── config.py            # Configuración de OpenAI (clave, modelo y límite de tokens)
├── docker-compose.yml   # MongoDB
├── requirements.txt
└── .env.example
```

## Verificación del CV generado

Cada CV optimizado pasa dos controles antes de descargarlo:

1. **Reglas automáticas** (sin IA): el PDF ocupa una página, su texto se puede extraer, se conservan email, teléfono y niveles de idioma, y no quedan campos `[COMPLETAR]`.
2. **Segunda revisión con IA**: compara el CV original con el generado y señala datos inventados, datos perdidos y errores de ortografía.

Es una comprobación práctica, no una garantía frente a un ATS concreto.

## Seguridad

- Las claves se leen desde variables de entorno y `.env` está en `.gitignore`.
- El `docker-compose.yml` expone MongoDB **sin contraseña** en el puerto 27017. Está pensado solo para desarrollo local: no lo uses tal cual en un servidor.

## Mejoras futuras

- Migrar a la versión actual del SDK de OpenAI.
- Tests automáticos.
- Despliegue online de la demo.

## Autor

**Freddy Materano**: [GitHub](https://github.com/freddyjmc)

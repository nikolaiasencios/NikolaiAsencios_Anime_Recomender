# Anime Recommender API

API de recomendación de animes desarrollada con FastAPI y Gemini.

Indicaciones de ejecución del docker:

1) En la terminal ejecutar lo siguiente para descargar el docker:

docker pull ghcr.io/nikolaiasencios/anime-recommender:d2420e989af6d48428c8082a720faabf8ec21be0

2) Ejecutar el docker reemplazando "YOUR KEY" por tu KEY de gemini.

$env:GOOGLE_API_KEY="YOUR KEY"

docker run -p 8000:8000 `
-e GOOGLE_API_KEY=$env:GOOGLE_API_KEY `
anime-recommender

3) Ingresar a la URL:

http://localhost:8000/docs

# Descripción de la app

El usuario describe sus preferencias en lenguaje natural (por ejemplo:
*"Quiero un anime psicológico corto"* o *"Recomiendame un anime como Dragon Ball Z"*).

Gemini interpreta las preferencias y las convierte en filtros estructurados.
Luego, un motor de scoring basado en reglas y métricas del dataset genera un
ranking de recomendaciones. Finalmente, Gemini redacta una explicación de los
resultados.

## Flujo

```text
Usuario escribe una preferencia
            ↓
Gemini extrae filtros
            ↓
Motor de scoring calcula puntajes
            ↓
Se genera el Top-N de animes
            ↓
Gemini explica las recomendaciones
```

## Tecnologías

- Python 3.12
- FastAPI
- Gemini API
- Pandas
- NumPy
- Pytest
- Flake8
- Docker
- GitHub Actions
- GitHub Container Registry (GHCR)

## Estructura del proyecto

```text
.
├── app/
│   └── main.py
├── data/
│   └── anime-dataset-2023.csv
├── tests/
│   └── test_api.py
├── requirements.txt
├── Dockerfile
├── .github/
│   └── workflows/
│       └── ci.yml
└── README.md
```

## Endpoints

### Health Check

```http
GET /
```

Respuesta:

```json
{
  "status": "ok",
  "model": "gemini-3.1-flash-lite-preview",
  "anime_count": 24905
}
```

### Recomendación de Anime

```http
POST /recommend
```

Request:

```json
{
  "query": "Quiero un anime psicológico corto"
}
```

Response:

```json
{
  "filters": {
    "genres": ["Psychological"],
    "max_episodes": 30
  },
  "recommendations": [
    {
      "title": "Death Note",
      "genres": "Mystery, Psychological, Supernatural",
      "score": 8.6
    }
  ],
  "explanation": "..."
}
```

## Ejecución Local

Instalar dependencias:

```bash
pip install -r requirements.txt
```

Configurar la API Key:

```bash
export GOOGLE_API_KEY="TU_API_KEY"
```

o en PowerShell:

```powershell
$env:GOOGLE_API_KEY="TU_API_KEY"
```

Ejecutar la API:

```bash
uvicorn app.main:app --reload
```

Documentación Swagger:

```text
http://localhost:8000/docs
```

## Docker

Construir imagen:

```bash
docker build -t anime-recommender .
```

Ejecutar contenedor:

```bash
docker run -p 8000:8000 \
-e GOOGLE_API_KEY=TU_API_KEY \
anime-recommender
```

En PowerShell:

```powershell
docker run -p 8000:8000 `
-e GOOGLE_API_KEY=$env:GOOGLE_API_KEY `
anime-recommender
```

## CI/CD

El proyecto cuenta con GitHub Actions para:

- Instalación automática de dependencias
- Lint con Flake8
- Tests con Pytest
- Build de imagen Docker
- Publicación automática en GitHub Container Registry (GHCR)

Workflow:

```text
.github/workflows/ci.yml
```

## GHCR

Las imágenes Docker se publican automáticamente en:

```text
ghcr.io/<usuario>/anime-recommender:<sha>
```

Cada commit genera una imagen versionada mediante el SHA de GitHub.

## Testing

Ejecutar pruebas:

```bash
pytest -q
```

## Autor

Nikolai Asencios Garcia

import json
import os
from contextlib import asynccontextmanager

import numpy as np
import pandas as pd
from fastapi import FastAPI, HTTPException
from google import genai
from google.genai import types
from pydantic import BaseModel
from pathlib import Path

# ============================================================================
# CONFIGURACIÓN
# ============================================================================

GOOGLE_API_KEY = os.environ.get("GOOGLE_API_KEY")

MODEL = "gemini-3.1-flash-lite-preview"

WEIGHTS = {
    "genres": 0.50,
    "episodes": 0.15,
    "type": 0.10,
    "score": 0.15,
    "popularity": 0.05,
    "favorites": 0.05,
}

gemini_client = None
anime_df = None

# ============================================================================
# LIFESPAN
# ============================================================================


@asynccontextmanager
async def lifespan(app: FastAPI):
    global gemini_client
    global anime_df

    if not GOOGLE_API_KEY:
        raise RuntimeError(
            "GOOGLE_API_KEY no encontrada en variables de entorno."
        )

    gemini_client = genai.Client(
        api_key=GOOGLE_API_KEY
    )

    print("[startup] Gemini inicializado.")

    BASE_DIR = Path(__file__).resolve().parent
    DATA_PATH = BASE_DIR.parent / "data" / "anime-dataset-2023.csv"

    anime_df = pd.read_csv(DATA_PATH)

    anime_df["Genres"] = anime_df["Genres"].fillna("")
    anime_df["Synopsis"] = anime_df["Synopsis"].fillna("")
    anime_df["Studios"] = anime_df["Studios"].fillna("")
    anime_df["Type"] = anime_df["Type"].fillna("")

    anime_df["Score"] = pd.to_numeric(
        anime_df["Score"],
        errors="coerce"
    ).fillna(0)

    anime_df["Episodes"] = pd.to_numeric(
        anime_df["Episodes"],
        errors="coerce"
    ).fillna(0)

    anime_df["Favorites"] = pd.to_numeric(
        anime_df["Favorites"],
        errors="coerce"
    ).fillna(0)

    anime_df["Scored By"] = pd.to_numeric(
        anime_df["Scored By"],
        errors="coerce"
    ).fillna(0)

    print(
        f"[startup] {len(anime_df)} animes cargados."
    )

    yield

    print("[shutdown] Cerrando app.")


# ============================================================================
# APP
# ============================================================================

app = FastAPI(
    title="Anime Recommender API",
    description="API de recomendación de anime usando Gemini + scoring",
    version="1.0.0",
    lifespan=lifespan,
)

# ============================================================================
# SCHEMAS
# ============================================================================


class RecommendRequest(BaseModel):
    query: str


class AnimeRecommendation(BaseModel):
    title: str
    english_name: str
    genres: str
    score: float
    episodes: int
    type: str
    studio: str
    recommendation_score: float


class RecommendResponse(BaseModel):
    filters: dict
    recommendations: list[AnimeRecommendation]
    explanation: str


# ============================================================================
# GEMINI - EXTRACCIÓN DE FILTROS
# ============================================================================


def extract_filters(user_query: str) -> dict:

    prompt = f"""
Eres un extractor de preferencias para un recomendador de anime.

Devuelve únicamente JSON válido.

Campos permitidos:

genres
max_episodes
type
rating

Tipos válidos:

TV
Movie
OVA
ONA
Special

Ejemplos:

Usuario:
Quiero un anime psicológico corto

Respuesta:
{{
    "genres": ["Psychological"],
    "max_episodes": 30
}}

Usuario:
Quiero una película de ciencia ficción

Respuesta:
{{
    "genres": ["Sci-Fi"],
    "type": "Movie"
}}

Consulta:

{user_query}
"""

    response = gemini_client.models.generate_content(
        model=MODEL,
        contents=prompt,
        config=types.GenerateContentConfig(
            temperature=0
        )
    )

    text = response.text.strip()

    text = text.replace("```json", "")
    text = text.replace("```", "")

    try:
        return json.loads(text)

    except Exception:
        return {}


# ============================================================================
# MOTOR DE SCORING
# ============================================================================


def calculate_recommendation_scores(df, filters):

    results = df.copy()

    # filtros mínimos de calidad

    results = results[
        results["Score"] >= 6
    ]

    results = results[
        results["Scored By"] >= 1000
    ]

    recommendation_score = np.zeros(len(results))

    # ------------------------------------------------------------------
    # GÉNEROS
    # ------------------------------------------------------------------

    genres = filters.get("genres", [])

    genre_scores = []

    for anime_genres in results["Genres"]:

        score = 0

        anime_genres = str(anime_genres)

        for genre in genres:

            if genre.lower() in anime_genres.lower():
                score += 1

        if len(genres) > 0:
            score = score / len(genres)

        genre_scores.append(score)

    recommendation_score += (
        np.array(genre_scores)
        * WEIGHTS["genres"]
        * 100
    )

    # ------------------------------------------------------------------
    # EPISODIOS
    # ------------------------------------------------------------------

    if "max_episodes" in filters:

        episode_scores = np.where(
            results["Episodes"]
            <= filters["max_episodes"],
            1.0,
            0.0
        )

        recommendation_score += (
            episode_scores
            * WEIGHTS["episodes"]
            * 100
        )

    # ------------------------------------------------------------------
    # TYPE
    # ------------------------------------------------------------------

    if "type" in filters:

        type_scores = np.where(
            results["Type"].str.lower()
            == filters["type"].lower(),
            1.0,
            0.0
        )

        recommendation_score += (
            type_scores
            * WEIGHTS["type"]
            * 100
        )

    # ------------------------------------------------------------------
    # SCORE MAL
    # ------------------------------------------------------------------

    score_component = (
        results["Score"] / 10
    )

    recommendation_score += (
        score_component
        * WEIGHTS["score"]
        * 100
    )

    # ------------------------------------------------------------------
    # POPULARIDAD
    # ------------------------------------------------------------------

    popularity_component = np.log1p(
        results["Scored By"]
    )

    max_pop = popularity_component.max()

    if max_pop > 0:
        popularity_component = (
            popularity_component / max_pop
        )

    recommendation_score += (
        popularity_component
        * WEIGHTS["popularity"]
        * 100
    )

    # ------------------------------------------------------------------
    # FAVORITOS
    # ------------------------------------------------------------------

    favorite_component = np.log1p(
        results["Favorites"]
    )

    max_fav = favorite_component.max()

    if max_fav > 0:
        favorite_component = (
            favorite_component / max_fav
        )

    recommendation_score += (
        favorite_component
        * WEIGHTS["favorites"]
        * 100
    )

    results["recommendation_score"] = (
        recommendation_score
    )

    return results.sort_values(
        "recommendation_score",
        ascending=False
    )


# ============================================================================
# GEMINI - EXPLICACIÓN
# ============================================================================


def build_explanation(
    user_query: str,
    recommendations: list[dict]
):

    prompt = f"""
Usuario:

{user_query}

Animes recomendados:

{json.dumps(recommendations, ensure_ascii=False, indent=2)}

Explica por qué estos animes son adecuados.

Máximo 250 palabras.

Habla de:

- géneros
- temática
- duración
- similitudes relevantes

No inventes información.
"""

    response = gemini_client.models.generate_content(
        model=MODEL,
        contents=prompt,
        config=types.GenerateContentConfig(
            temperature=0.3
        )
    )

    return response.text


# ============================================================================
# ENDPOINTS
# ============================================================================


@app.get("/")
async def root():

    return {
        "status": "ok",
        "model": MODEL,
        "anime_count": len(anime_df)
    }


@app.post(
    "/recommend",
    response_model=RecommendResponse
)
async def recommend(
    request: RecommendRequest
):

    filters = extract_filters(
        request.query
    )

    results = calculate_recommendation_scores(
        anime_df,
        filters
    )

    if len(results) == 0:
        raise HTTPException(
            status_code=404,
            detail="No se encontraron animes."
        )

    top_5 = results.head(5)

    recommendations = []

    for _, row in top_5.iterrows():

        recommendations.append(
            {
                "title": str(row["Name"]),
                "english_name": str(
                    row["English name"]
                ),
                "genres": str(
                    row["Genres"]
                ),
                "score": float(
                    row["Score"]
                ),
                "episodes": int(
                    row["Episodes"]
                ),
                "type": str(
                    row["Type"]
                ),
                "studio": str(
                    row["Studios"]
                ),
                "recommendation_score": round(
                    float(
                        row[
                            "recommendation_score"
                        ]
                    ),
                    2
                ),
            }
        )

    explanation = build_explanation(
        request.query,
        recommendations
    )

    return {
        "filters": filters,
        "recommendations": recommendations,
        "explanation": explanation,
    }

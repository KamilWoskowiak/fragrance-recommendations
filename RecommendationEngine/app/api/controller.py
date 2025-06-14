from fastapi import APIRouter, HTTPException, Depends
from typing import List

from app.config import ACCORD_COLS
from app.model.schemas import RecommendationRequest, RecommendationResponse, AccordBasedRecommendationRequest
from app.service.recommender import FragranceRecommender
from fastapi_limiter.depends import RateLimiter

router = APIRouter()
recommender = FragranceRecommender()
sorted_fragrances = sorted(list(recommender.valid_names_brands))
sorted_accords = sorted(ACCORD_COLS)


@router.get("/", dependencies=[Depends(RateLimiter(times=5, seconds=60))])
async def root():
    return {"message": "Fragrance Recommendation API"}


@router.get("/fragrances", dependencies=[Depends(RateLimiter(times=5, seconds=60))])
async def list_fragrances():
    return {"fragrances": sorted_fragrances}

@router.get("/accords", dependencies=[Depends(RateLimiter(times=5, seconds=60))])
async def list_fragrances_accord():
    return {"accords": sorted_accords}


@router.post("/recommend-by-fragrances", response_model=List[RecommendationResponse], dependencies=[Depends(RateLimiter(times=10, seconds=60))])
async def recommend_fragrances(request: RecommendationRequest):
    try:
        invalid_names = [name for name in request.liked_fragrances
                         if name not in recommender.valid_names]
        if invalid_names:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid fragrance names: {', '.join(invalid_names)}"
            )

        user_vector = recommender.build_user_profile(request.liked_fragrances)
        recommendations = recommender.get_recommendations(
            user_vector,
            request.time_pref,
            request.season_pref,
            request.top_k,
            request.diversity_factor
        )

        return recommendations

    except Exception as e:
        print(e)
        raise HTTPException(
            status_code=500,
            detail=f"An error occurred while processing your request: {str(e)}"
        )

@router.post("/recommend-by-accords", response_model=List[RecommendationResponse], dependencies=[Depends(RateLimiter(times=10, seconds=60))])
async def recommend_fragrances_by_accords(request: AccordBasedRecommendationRequest):
    try:
        invalid_accords = set(request.accord_preferences.keys()) - set(ACCORD_COLS)
        if invalid_accords:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid accord names: {', '.join(invalid_accords)}"
            )

        invalid_weights = [
            accord for accord, weight in request.accord_preferences.items()
            if not 0 <= weight <= 1
        ]
        if invalid_weights:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid weights for accords: {', '.join(invalid_weights)}. Weights must be between 0 and 1."
            )

        recommendations = recommender.get_recommendations_by_accords(
            accord_preferences=request.accord_preferences,
            time_pref=request.time_pref,
            season_pref=request.season_pref,
            top_k=request.top_k,
            diversity_factor=request.diversity_factor
        )

        return recommendations

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"An error occurred while processing your request: {str(e)}"
        )
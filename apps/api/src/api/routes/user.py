"""User routes handling favorites and user-specific actions."""

from fastapi import APIRouter, HTTPException, Query

from api.models.api_models import (
    RequestFavorite,
    FavoriteResponse,
    ResponseFavorites,
)
from api.models.db_models import Domain as DomainDB, Favorite as FavoriteDB


router = APIRouter(prefix="/user", tags=["user"])


@router.post("/favorite")
async def toggle_favorite(
    request: RequestFavorite,
) -> dict:
    """
    Favorite or unfavorite a domain.
    
    - Requires user_id in request body
    - Domain must exist in database
    - action: 'fav' to favorite, 'unfav' to unfavorite
    """
    domain_obj = await DomainDB.get_or_none(domain=request.domain)
    if not domain_obj:
        raise HTTPException(
            status_code=400,
            detail="Domain not found"
        )
    
    try:
        if request.action == "fav":
            existing_favorite = await FavoriteDB.get_or_none(
                domain=domain_obj,
                user_id=request.user_id
            )
            if existing_favorite:
                return {
                    "success": True,
                    "action": "fav",
                    "domain": request.domain,
                    "message": "Domain already favorited"
                }
            
            favorite = await FavoriteDB.create(
                domain=domain_obj,
                user_id=request.user_id,
            )
            return {
                "success": True,
                "action": "fav",
                "domain": request.domain,
                "favorite_id": favorite.id,
            }
        elif request.action == "unfav":
            existing_favorite = await FavoriteDB.get_or_none(
                domain=domain_obj,
                user_id=request.user_id
            )
            if not existing_favorite:
                return {
                    "success": True,
                    "action": "unfav",
                    "domain": request.domain,
                    "message": "Domain not favorited"
                }
            
            await existing_favorite.delete()
            return {
                "success": True,
                "action": "unfav",
                "domain": request.domain,
            }
        else:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid action: {request.action}. Must be 'fav' or 'unfav'"
            )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to toggle favorite: {str(e)}"
        )


@router.get("/favorite")
async def get_favorites(
    user_id: str | None = Query(None, description="User ID (required)"),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Number of items per page"),
) -> ResponseFavorites:
    """
    Get all favorited domains for a user.
    
    Requires user_id as query parameter.
    Returns paginated results.
    """
    if not user_id:
        raise HTTPException(
            status_code=400,
            detail="User ID is required"
        )
    
    total = await FavoriteDB.filter(user_id=user_id).count()
    
    offset = (page - 1) * page_size
    favorites = await FavoriteDB.filter(user_id=user_id).order_by("-created_at").offset(offset).limit(page_size).prefetch_related("domain")
    
    favorite_responses = [
        FavoriteResponse(
            id=favorite.id,
            domain=favorite.domain.domain,
            created_at=favorite.created_at,
        )
        for favorite in favorites
    ]
    
    return ResponseFavorites(
        favorites=favorite_responses,
        total=total,
        page=page,
        page_size=page_size,
    )


import datetime

from fastapi import APIRouter

from api.models.api_models import DomainStatus, DomainSuggestion, RequestDomainSuggestion, ResponseDomainSuggestion
from api.models.api_models import ResponseDomainStatus
from api.suggestor.groq import GroqSuggestor

router = APIRouter(prefix="/domain", tags=["domain"])

@router.get("/")
def get_domain_status(domain: str) -> ResponseDomainStatus:
    """
    Get the status of a domain.
    """
    return ResponseDomainStatus(status=DomainStatus.AVAILABLE)

@router.post("/")
async def suggest(request: RequestDomainSuggestion) -> ResponseDomainSuggestion:
    """
    Generate domain suggestions based on the user input.
    """
    domain_suggestions = await GroqSuggestor().generate(request.description, request.count)

    return_suggestions = []
    for domain_suggestion in domain_suggestions:
        #status = get_domain_status(domain_suggestion.domain)
        return_suggestions.append(DomainSuggestion(domain=domain_suggestion, tld=domain_suggestion.split(".")[-1], status=DomainStatus.UNKNOWN, created_at=datetime.datetime.now(datetime.UTC), updated_at=datetime.datetime.now(datetime.UTC)))


    return ResponseDomainSuggestion(suggestions=return_suggestions, total=len(return_suggestions))
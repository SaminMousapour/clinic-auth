import logging
from django.http import HttpResponse

logger = logging.getLogger(__name__)


def custom_500(request, *args, **kwargs):
    try:
        exc = args[0] if args else kwargs.get('exception')
        logger.error("500 ERROR | Path: %s | User: %s | Exception: %s", request.path, request.user, exc, exc_info=True)
    except Exception:
        pass
    return HttpResponse('<h1>500 - Server Error</h1><p>Please try again in a moment.</p>', status=500)

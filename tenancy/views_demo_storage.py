from django.views.decorators.http import require_GET

from caixa.permissions import (
    api_authentication_required_response,
    api_no_store_json_response,
)
from tenancy.services_demo_storage import (
    demo_storage_quota_applies,
    get_demo_storage_quota_status,
)


@require_GET
def api_demo_storage_quota(request):
    if not request.user.is_authenticated:
        return api_authentication_required_response()

    if not demo_storage_quota_applies(request.user):
        return api_no_store_json_response(
            {
                "storageQuota": {
                    "applies": False,
                    "usedBytes": 0,
                    "maxBytes": 0,
                    "maxStorageMb": 0,
                    "exceeded": False,
                    "measuredAt": None,
                }
            }
        )

    status = get_demo_storage_quota_status(use_cache=True)
    return api_no_store_json_response({"storageQuota": status.as_payload()})

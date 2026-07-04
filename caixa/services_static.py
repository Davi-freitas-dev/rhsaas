from django.contrib.staticfiles import finders
from django.http import FileResponse, Http404


def static_file_response(static_path, content_type, not_found_message, headers=None):
    file_path = finders.find(static_path)
    if not file_path:
        raise Http404(not_found_message)

    response = FileResponse(open(file_path, "rb"), content_type=content_type)

    for key, value in (headers or {}).items():
        response[key] = value

    return response

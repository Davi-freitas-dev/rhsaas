import json
from pathlib import Path
from uuid import uuid4

from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
from django.core.mail.backends.base import BaseEmailBackend


class JsonFileEmailBackend(BaseEmailBackend):
    """Write test messages as JSON for a separate browser process."""

    def send_messages(self, email_messages):
        if not settings.PASSWORD_RESET_E2E_ENABLED:
            raise ImproperlyConfigured(
                "JsonFileEmailBackend exige PASSWORD_RESET_E2E_ENABLED=True."
            )

        output_dir = Path(settings.EMAIL_FILE_PATH)
        output_dir.mkdir(parents=True, exist_ok=True)
        sent = 0
        for message in email_messages or ():
            target = output_dir / f"{uuid4().hex}.json"
            temporary = target.with_suffix(".tmp")
            temporary.write_text(
                json.dumps(
                    {
                        "body": message.body,
                        "fromEmail": message.from_email,
                        "subject": message.subject,
                        "to": list(message.to or ()),
                    },
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )
            temporary.replace(target)
            sent += 1

        return sent

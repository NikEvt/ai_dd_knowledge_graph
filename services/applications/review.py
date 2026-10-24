from services.applications.models import Client

REQUIRED_CLIENT_FIELDS = ("full_name", "passport", "birth_date")


def missing_client_fields(client: Client) -> list[str]:
    return [f for f in REQUIRED_CLIENT_FIELDS if not getattr(client, f)]

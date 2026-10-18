from nova_post_bot.clients.nova_post import NovaPostClient
from nova_post_bot.core.exceptions import NovaPostValidationError
from nova_post_bot.schemas.tracking import TrackingInfo


class TrackingService:
    def __init__(self, nova_post_client: NovaPostClient):
        self.nova_post_client = nova_post_client

    async def get_tracking_info(self, number: str) -> list[TrackingInfo]:
        if not isinstance(number, str):
            raise NovaPostValidationError("Tracking number must be a string")
        number = number.strip()
        if not number:
            raise NovaPostValidationError("Tracking number cannot be empty")

        if not number.isascii() or not number.isdigit():
            raise NovaPostValidationError("Tracking number must contain only digits")
        if len(number) != 14:
            raise NovaPostValidationError("Tracking number must contain exactly 14 digits")
        return await self.nova_post_client.get_tracking_info(number=number)




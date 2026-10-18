import httpx
import pydantic
import time
import logging

from nova_post_bot.core.exceptions import NovaPostUnexpectedResponseError, NovaPostAPIError, NovaPostTimeoutError, \
    NovaPostConnectionError, NovaPostValidationError
from nova_post_bot.schemas.tracking import TrackingInfo

logger = logging.getLogger(__name__)


class NovaPostClient:
    def __init__(self,
                 api_key: str,
                 base_url: str,
                 timeout: float):
        self.api_key = api_key
        self.http_client = httpx.AsyncClient(base_url=base_url, timeout=timeout)

    async def close(self):
        await self.http_client.aclose()

    async def _request(self, model_name: str,
                       called_method: str,
                       method_properties: dict):

        if not isinstance(model_name, str):
            raise NovaPostValidationError("model_name must be a string")
        if model_name.strip() == "":
            raise NovaPostValidationError("model_name cannot be empty")

        if not isinstance(called_method, str):
            raise NovaPostValidationError("called_method must be a string")
        if called_method.strip() == "":
            raise NovaPostValidationError("called_method cannot be empty")

        if not isinstance(method_properties, dict):
            raise NovaPostValidationError("method_properties must be a dictionary")

        payload = {"apiKey": self.api_key,
                   "modelName": model_name,
                   "calledMethod": called_method,
                   "methodProperties": method_properties}

        started_at = time.perf_counter()
        try:
            response = await self.http_client.post("", json=payload)
            response.raise_for_status()
        except httpx.TimeoutException as exc:
            logger.warning("Nova Post API operation: method=%s, success=False reason=timeout",
                           called_method)
            raise NovaPostTimeoutError("Nova Post request timed out") from exc
        except httpx.ConnectError as exc:
            logger.warning("Nova Post API operation: method=%s, success=False reason=connection_error",
                           called_method)
            raise NovaPostConnectionError("Could not connect to Nova Post API") from exc
        except httpx.HTTPStatusError as exc:
            logger.warning("Nova Post API operation: method=%s, success=False reason=http_error status_code=%d",
                           called_method, exc.response.status_code)
            raise NovaPostAPIError(f"Nova Post API returned HTTP {exc.response.status_code}") from exc
        except httpx.RequestError as exc:
            logger.warning("Nova Post API operation: method=%s, success=False reason=request_error",
                           called_method)
            raise NovaPostConnectionError("Nova Post request failed") from exc
        finally:
            duration = time.perf_counter() - started_at
            logger.info("Nova Post HTTP request: method=%s duration=%.3f s", called_method, duration)

        try:
            json_response = response.json()
        except ValueError as exc:
            logger.warning("Nova Post API operation: method=%s success=False reason=invalid_json",
                           called_method)
            raise NovaPostUnexpectedResponseError("Response is not valid JSON") from exc

        if not isinstance(json_response, dict):
            logger.warning("Nova Post API operation: method=%s success=False reason=invalid_response_type",
                           called_method)
            raise NovaPostUnexpectedResponseError("Expected a JSON obj")

        success = json_response.get("success")
        if not isinstance(success, bool):
            logger.warning("Nova Post API operation: method=%s success=False reason=invalid_success_type",
                           called_method)
            raise NovaPostUnexpectedResponseError("Expected a boolean 'success' field")
        if not success:
            error_codes = json_response.get("errorCodes")
            invalid_number_code = "20001401442"
            if isinstance(error_codes, list):
                if invalid_number_code in error_codes:
                    logger.warning(
                        "Nova Post API operation: method=%s success=False reason=invalid_tracking_number",
                        called_method,
                    )
                    raise NovaPostValidationError("Nova Post rejected the tracking number")

            logger.warning("Nova Post API operation: method=%s success=False, reason=api_error",
                           called_method)
            raise NovaPostAPIError("Nova Post API reported an error")

        data = json_response.get("data")
        if not isinstance(data, list):
            logger.warning("Nova Post API operation: method=%s success=False reason=invalid_data_type",
                           called_method)
            raise NovaPostUnexpectedResponseError("Expected a list 'data' field")
        logger.info("Nova Post API operation: method=%s success=%s count=%d", called_method, success, len(data))
        return data

    def _parse_tracking(self, tracking_data: list) -> list[TrackingInfo]:
        try:
            tracking_items = [TrackingInfo.model_validate(item) for item in tracking_data]
        except pydantic.ValidationError as exc:
            raise NovaPostUnexpectedResponseError("Invalid tracking response") from exc
        return tracking_items

    async def get_tracking_info(self, number: str) -> list[TrackingInfo]:
        if not isinstance(number, str):
            raise NovaPostValidationError("Number must be a string")
        ttn = number.strip()
        if ttn == "":
            raise NovaPostValidationError("Number cannot be empty")
        method_properties = {"Documents": [{"DocumentNumber": ttn}]}

        data = await self._request(model_name="TrackingDocumentGeneral",
                                   called_method="getStatusDocuments",
                                   method_properties=method_properties)

        return self._parse_tracking(data)

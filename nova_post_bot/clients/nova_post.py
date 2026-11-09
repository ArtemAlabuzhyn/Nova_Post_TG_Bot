import logging
import time

import httpx
import pydantic

from nova_post_bot.core.exceptions import NovaPostUnexpectedResponseError, NovaPostAPIError, NovaPostTimeoutError, \
    NovaPostConnectionError, NovaPostValidationError, NovaPostRejectedError
from nova_post_bot.schemas.city import CityInfo
from nova_post_bot.schemas.contact_person import ContactPersonInfo
from nova_post_bot.schemas.shipment import CreatedShipmentInfo
from nova_post_bot.schemas.tracking import TrackingInfo
from nova_post_bot.schemas.warehouse import WarehouseInfo

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
            if (model_name == "TrackingDocumentGeneral"
                    and called_method == "getStatusDocuments"
                    and isinstance(error_codes, list)):
                if invalid_number_code in error_codes:
                    logger.warning(
                        "Nova Post API operation: method=%s success=False reason=invalid_tracking_number",
                        called_method,
                    )
                    raise NovaPostValidationError("Nova Post rejected the tracking number")

            logger.warning("Nova Post API operation: method=%s success=False, reason=api_error",
                           called_method)
            raise NovaPostRejectedError("Nova Post API reported an error")

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

    async def search_cities(self, query: str) -> list[CityInfo]:
        query = self._normalize_required_string(query, "Query")
        data = await self._request(model_name="Address",
                                   called_method="getCities",
                                   method_properties={"FindByString": query})
        return self._parse_cities(data)

    def _parse_cities(self, cities_data: list) -> list[CityInfo]:
        try:
            cities = [CityInfo.model_validate(item) for item in cities_data]
        except pydantic.ValidationError as exc:
            raise NovaPostUnexpectedResponseError("Invalid city response") from exc
        return cities

    async def search_warehouses(self, city_ref: str, query: str) -> list[WarehouseInfo]:
        city_ref = self._normalize_required_string(city_ref, "CityRef")
        query = self._normalize_required_string(query, "Query")
        if not query.isascii() or not query.isdigit():
            raise NovaPostValidationError("Warehouse number must contain only digits")
        data = await self._request(model_name="Address", called_method="getWarehouses",
                                   method_properties={"CityRef": city_ref,
                                                      "FindByString": f"№{query}"})
        return self._parse_warehouse(data)

    def _parse_warehouse(self, warehouse_data: list) -> list[WarehouseInfo]:
        try:
            warehouses = [WarehouseInfo.model_validate(item) for item in warehouse_data]
        except pydantic.ValidationError as exc:
            raise NovaPostUnexpectedResponseError("Invalid warehouse response") from exc
        return warehouses

    @staticmethod
    def _normalize_required_string(value: str, field_name: str) -> str:
        if not isinstance(value, str):
            raise NovaPostValidationError(f"{field_name} must be a string")

        value = value.strip()
        if not value:
            raise NovaPostValidationError(f"{field_name} cannot be empty")
        return value

    async def get_sender_counterparties(self) -> list[dict]:
        return await self._request(
            model_name="Counterparty",
            called_method="getCounterparties",
            method_properties={
                "CounterpartyProperty": "Sender",
                "Page": "1",
            }
        )

    async def get_counterparty_contact_persons(self, counterparty_ref: str, page: int = 1) -> list[dict]:
        counterparty_ref = self._normalize_required_string(counterparty_ref,
                                                           "CounterpartyRef")
        if page < 1:
            raise NovaPostValidationError("Page number must be 1")

        return await self._request(
            model_name="Counterparty",
            called_method="getCounterpartyContactPersons",
            method_properties={
                "Ref": counterparty_ref,
                "Page": str(page)
            }
        )

    async def search_sender_warehouses(self,
                                       city_ref: str,
                                       query: str) -> list[WarehouseInfo]:
        warehouses = await self.search_warehouses(city_ref=city_ref, query=query)
        return [
            warehouse for warehouse in warehouses
            if warehouse.category == "Branch"
        ]

    async def get_recipient_counterparties(self, page: int = 1) -> list[dict]:
        if page < 1:
            raise NovaPostValidationError("Page number must be at least 1")

        return await self._request(
            model_name="Counterparty",
            called_method="getCounterparties",
            method_properties={
                "CounterpartyProperty": "Recipient",
                "Page": str(page),
            }
        )

    async def create_shipment(self, method_properties: dict) -> CreatedShipmentInfo:
        data = await self._request(model_name="InternetDocumentGeneral",
                                   called_method="save",
                                   method_properties=method_properties)
        if len(data) != 1:
            raise NovaPostUnexpectedResponseError(
                f"Expected 1 created shipment, got {len(data)}"
            )
        try:
            result = CreatedShipmentInfo.model_validate(data[0])
        except pydantic.ValidationError as exc:
            raise NovaPostUnexpectedResponseError("Invalid shipment response") from exc

        return result

    async def create_contact_person(self, first_name: str,
                                    last_name: str, phone: str,
                                    counterparty_ref: str) -> ContactPersonInfo:
        first_name = self._normalize_required_string(first_name, "FirstName")
        last_name = self._normalize_required_string(last_name, "LastName")
        phone = self._normalize_required_string(phone, "Phone")
        counterparty_ref = self._normalize_required_string(counterparty_ref, "CounterpartyRef")
        data = await self._request(model_name="ContactPersonGeneral",
                                   called_method="save",
                                   method_properties={
                                       "CounterpartyRef": counterparty_ref,
                                       "FirstName": first_name,
                                       "LastName": last_name,
                                       "Phone": phone,
                                       "MiddleName": ""
                                   })

        if len(data) != 1:
            raise NovaPostUnexpectedResponseError(
                f"Expected 1 created contact person, got {len(data)}"
            )
        try:
            result = ContactPersonInfo.model_validate(data[0])
        except pydantic.ValidationError as exc:
            raise NovaPostUnexpectedResponseError("Invalid contact person response") from exc

        return result

    async def get_shipment_pdf(self, document_ref: str) -> bytes:
        payload = {
            "apiKey": self.api_key,
            "modelName": "InternetDocument",
            "calledMethod": "printFull",
            "methodProperties": {
                "DocumentRefs": [document_ref],
                "Type": "pdf",
                "printForm": "Document_new",
                "PageFormat": "A4",
                "Position": "1",
                "Copies": "1",
            },
        }

        response = await self.http_client.post("", json=payload)
        response.raise_for_status()

        if not response.content.startswith(b"%PDF-"):
            try:
                body = response.json()
            except ValueError:
                body = None

            error_codes = body.get("errorCodes") if isinstance(body, dict) else None
            content_type = response.headers.get("Content-Type", "не указан")
            raise NovaPostUnexpectedResponseError(
                f"printFull did not return a PDF: HTTP {response.status_code}, "
                f"Content-Type: {content_type}, errorCodes: {error_codes!r}"
            )

        return response.content

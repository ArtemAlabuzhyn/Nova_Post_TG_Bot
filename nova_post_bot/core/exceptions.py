

class ObjectNotFoundError(Exception):
    def __init__(self, object_id, object_name: str = "Object"):
        self.object_id = object_id
        self.object_name = object_name
        super().__init__(f"{object_name}: not found")

class NovaPostAPIError(Exception):
    pass

class NovaPostUnexpectedResponseError(NovaPostAPIError):
    pass

class NovaPostTimeoutError(NovaPostAPIError):
    pass

class NovaPostConnectionError(NovaPostAPIError):
    pass

class NovaPostValidationError(NovaPostAPIError):
    pass
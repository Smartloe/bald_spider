class TransformTypeError(TypeError):
    pass


class OutputError(Exception):
    pass


class SpiderTypeError(TypeError):
    pass


class ItemInError(Exception):
    pass


class ItemAttribuError(Exception):
    pass


class DecodeError(Exception):
    pass


class MiddlewareInitError(Exception):
    pass


class InvalidOutputError(Exception):
    pass


class RequestMethodError(Exception):
    pass


class IgnoreRequest(Exception):
    def __init__(self, msg) -> None:
        self.msg = msg
        super(IgnoreRequest, self).__init__(msg)


class NotConfigured(Exception):
    pass

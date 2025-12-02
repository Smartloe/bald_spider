class BaseMiddleware:
    def process_request(self, request, spider):
        print("test middleware")
        return None

    def process_response(self, request, response, spider):
        print("test middleware response")
        return response

    def process_exception(self, request, exception, spider):
        print("test middleware exception")
        return None
    @classmethod
    def create_instance(cls, crawler):
        return cls()

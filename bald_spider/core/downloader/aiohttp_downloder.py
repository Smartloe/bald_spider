from bald_spider import Response
from aiohttp import ClientSession, TCPConnector, BaseConnector, ClientTimeout, ClientResponse, TraceConfig
from bald_spider.core.downloader import DownloaderBase


class AioDownloader(DownloaderBase):

    def __init__(self, crawler):
        super().__init__(crawler)
        self.session: ClientSession | None = None
        self.connector: BaseConnector | None = None
        self._verify_ssl: bool | None = None
        self._timeout: ClientTimeout | None = None
        self._use_session: bool | None = None
        self.tace_config: TraceConfig | None = None
        self.request_method = {"get": self._get, "post": self._post}

    def open(self):
        super().open()
        request_timeout = self.crawler.settings.getint("REQUEST_TIMEOUT")
        self._timeout = ClientTimeout(total=request_timeout)
        self._verify_ssl = self.crawler.settings.getbool("VERIFY_SSL")
        self._use_session = self.crawler.settings.getbool("USE_SESSION")
        self.tace_config = TraceConfig()
        self.tace_config.on_request_start.append(self.request_start)
        if self._use_session:
            self.connector = TCPConnector(verify_ssl=self._verify_ssl)
            self.session = ClientSession(
                connector=self.connector, timeout=self._timeout, trace_configs=[self.tace_config]
            )

    async def download(self, request) -> Response | None:
        try:
            if self._use_session and self.session:
                response = await self.send_request(self.session, request)
                body = await response.content.read()
            else:
                connector = TCPConnector(verify_ssl=self._verify_ssl)
                async with ClientSession(
                    connector=connector, timeout=self._timeout, trace_configs=[self.tace_config]
                ) as session:
                    response = await self.send_request(session, request)
                    body = await response.content.read()
        except Exception as e:
            self.logger.error(f"Error during request: {e}")
            return None
        else:
            self.crawler.stats.inc_value("response_received_count")

        return self.structure_response(request, response, body)

    @staticmethod
    def structure_response(request, response, body):
        return Response(
            url=request.url, headers=dict(response.headers), body=body, request=request, status_code=response.status
        )

    async def send_request(self, session, request) -> ClientResponse:
        return await self.request_method[request.method.lower()](session, request)

    @staticmethod
    async def _get(session, request) -> ClientResponse:
        response = await session.get(
            request.url,
            headers=request.headers,
            cookies=request.cookie,
            proxy=request.proxy,
        )
        return response

    @staticmethod
    async def _post(session, request) -> ClientResponse:
        response = await session.post(
            request.url,
            data=request.body,
            headers=request.headers,
            cookies=request.cookie,
            proxy=request.proxy,
        )
        return response

    async def request_start(self, session, trace_config_ctx, params):
        self.logger.debug(f"request downloading: {params.url}, method: {params.method}")

    async def close(self):
        """关闭 downloader，清理资源"""
        if self.connector:
            await self.connector.close()
        if self.session:
            await self.session.close()

from bald_spider import Response
from bald_spider.core.downloader import DownloaderBase
import httpx


class HTTPXDownloader(DownloaderBase):
    def __init__(self, crawler):
        super().__init__(crawler)
        self._client: httpx.AsyncClient | None = None
        self._timeout: httpx.Timeout | None = None

    def open(self):
        super().open()
        request_timeout = self.crawler.settings.getint("REQUEST_TIMEOUT")
        self._timeout = httpx.Timeout(timeout=request_timeout)

    async def download(self, request) -> Response | None:
        try:
            proxies = request.proxy
            async with httpx.AsyncClient(timeout=self._timeout, proxy=proxies) as client:
                self.logger.debug(f"request downloading: {request.url}, method: {request.method}")
                response = await client.request(
                    method=request.method,
                    url=request.url,
                    headers=request.headers,
                    cookies=request.cookie,
                    data=request.body,
                )
                body = await response.aread()
        except Exception as e:
            self.logger.error(f"Error during request: {e}")
            return None
        else:
            self.crawler.stats.inc_value("response_received_count")

        return self.structure_response(request, response, body)

    @staticmethod
    def structure_response(request, response, body):
        return Response(
            url=request.url,
            headers=dict(response.headers),
            body=body,
            request=request,
            status_code=response.status_code,
        )

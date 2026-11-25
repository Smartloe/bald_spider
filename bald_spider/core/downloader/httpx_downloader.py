from bald_spider import Response
from bald_spider.core.downloader import DownloaderBase
import httpx


class HTTPXDownloader(DownloaderBase):
    def __init__(self, crawler):
        super().__init__(crawler)
        self._client: httpx.AsyncClient | None = None
        self._timeout: httpx.Timeout | None = None
        self._verify_ssl: bool = True
        self._use_session: bool = False

    def open(self):
        super().open()
        request_timeout = self.crawler.settings.getint("REQUEST_TIMEOUT")
        self._timeout = httpx.Timeout(timeout=request_timeout)
        self._verify_ssl = self.crawler.settings.getbool("VERIFY_SSL")
        self._use_session = self.crawler.settings.getbool("USE_SESSION")
        if self._use_session:
            self._client = httpx.AsyncClient(
                timeout=self._timeout,
                verify=self._verify_ssl,
                follow_redirects=True,
            )

    async def _request(self, client, request):
        self.logger.debug(f"request downloading: {request.url}, method: {request.method}")
        response = await client.request(
            method=request.method,
            url=request.url,
            headers=request.headers,
            cookies=request.cookie,
            data=request.body,
        )
        body = await response.aread()
        return response, body

    async def download(self, request) -> Response | None:
        try:
            if self._client is not None and request.proxy is None:
                response, body = await self._request(self._client, request)
            else:
                # 指定了 per-request 代理时无法复用共享 client，退化为一次性 client。
                async with httpx.AsyncClient(
                    timeout=self._timeout,
                    proxy=request.proxy,
                    verify=self._verify_ssl,
                    follow_redirects=True,
                ) as client:
                    response, body = await self._request(client, request)
        except Exception as e:
            self.logger.error(f"Error during request: {e}")
            raise e

        return self.structure_response(request, response, body)

    async def close(self):
        """关闭复用的 client，释放连接。"""
        if self._client is not None:
            await self._client.aclose()
            self._client = None

    @staticmethod
    def structure_response(request, response, body):
        # 使用下载器返回的最终 URL，确保重定向后的相对链接解析正确。
        return Response(
            url=str(response.url),
            headers=dict(response.headers),
            body=body,
            request=request,
            status_code=response.status_code,
        )

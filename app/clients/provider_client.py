import httpx
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type
from core.config import settings
from models.schemas import TransactionRequest
##Sets the provider client, in this case WireMock
class ProviderClient:
    def __init__(self):
        self.base_url = settings.PROVIDER_URL
        self.timeout = settings.PROVIDER_TIMEOUT#5 seconds

    @retry(
        stop=stop_after_attempt(settings.PROVIDER_RETRIES),
        wait=wait_exponential(multiplier=1, min=2, max=10),##so everytime it retries it has to wait more time, until 10 tries
        retry=retry_if_exception_type((httpx.TimeoutException, httpx.ConnectError)),
        reraise=True  ## raise the original httpx exception instead of wrapping it in a RetryError once retries are exhausted
    )
    def execute(self, request: TransactionRequest) -> dict:
        ##sends the transaction to Wirmock and return parsed response
        ##Launch expection if fails after retries or if provider returns error 5xx (Internal server error)
        url = f"{self.base_url}/provider/v1/execute"
        payload = request.dict(exclude_none=True)

        with httpx.Client(timeout=self.timeout) as client:
            response = client.post(url, json=payload)

            ## If provider fails we return 500 we dont retry, retring woll not fix, better fail quick and report the problem
            if response.status_code >= 500:
                response.raise_for_status()

            # For case 4xx we don'r retry, me only return JSON with error.
            if response.status_code >= 400:
                return response.json()

            # great succes!! (2xx)
            return response.json()

import json
import re
import time
from dataclasses import dataclass
from typing import Any, Callable, Generic, Optional, TypeVar
from urllib.error import HTTPError, URLError
from urllib.parse import quote, urlencode
from urllib.request import Request, urlopen


T = TypeVar('T')


class RequestError(Exception):
	"""Structured error for request failures."""

	def __init__(
		self,
		message: str,
		url: str,
		method: str,
		status_code: Optional[int] = None,
		attempts: int = 1,
		response_body: Optional[str] = None,
	):
		super().__init__(message)
		self.message = message
		self.url = url
		self.method = method
		self.status_code = status_code
		self.attempts = attempts
		self.response_body = response_body


@dataclass(frozen=True)
class RequestConfig:
	timeout: int = 15
	retries: int = 2
	backoff_factor: float = 0.5
	retry_on_status: tuple[int, ...] = (429, 500, 502, 503, 504)


class RequestClient(Generic[T]):
	"""HTTP request client with generic typed response handling and retries."""

	def __init__(
		self,
		config: Optional[RequestConfig] = None,
		logger: Optional[Callable[[str], None]] = None,
	):
		self.config = config or RequestConfig()
		self.logger = logger

	def request(
		self,
		url: str,
		*,
		method: str = 'GET',
		headers: Optional[dict[str, str]] = None,
		path_params: Optional[dict[str, Any]] = None,
		params: Optional[dict[str, Any]] = None,
		json_body: Optional[dict[str, Any] | list[Any]] = None,
		data: Optional[bytes | str] = None,
		parser: Optional[Callable[[Any], T]] = None,
		expected_type: Optional[type[T]] = None,
		default: Optional[T] = None,
		raise_on_error: bool = False,
	) -> Optional[T]:
		"""
		Send an HTTP request and return response in the requested type.

		Use `parser` for custom mapping, or `expected_type` for simple type conversion.
		"""
		try:
			request_url = self._build_url(url, params, path_params)
		except ValueError as exc:
			last_error = RequestError(
				message=f'Invalid URL path params: {exc}',
				url=url,
				method=method.upper(),
				attempts=1,
			)
			self._log(
				f'Request failed: {last_error.method} {last_error.url} '
				f'({last_error.message})'
			)
			if raise_on_error:
				raise last_error
			return default

		request_headers = dict(headers or {})

		if json_body is not None:
			payload = json.dumps(json_body).encode('utf-8')
			request_headers.setdefault('Content-Type', 'application/json')
		elif data is None:
			payload = None
		elif isinstance(data, str):
			payload = data.encode('utf-8')
		else:
			payload = data

		last_error: Optional[RequestError] = None
		total_attempts = self.config.retries + 1

		for attempt in range(1, total_attempts + 1):
			try:
				request = Request(
					url=request_url,
					data=payload,
					headers=request_headers,
					method=method.upper(),
				)
				with urlopen(request, timeout=self.config.timeout) as response:
					status_code = response.getcode()
					raw_body = response.read()

					if (
						status_code in self.config.retry_on_status
						and attempt < total_attempts
					):
						self._wait_before_retry(attempt)
						continue

					decoded = self._decode_response(raw_body)
					return self._convert_response(decoded, parser, expected_type)

			except HTTPError as exc:
				error_body = self._read_error_body(exc)
				last_error = RequestError(
					message=f'HTTP error {exc.code} during request.',
					url=request_url,
					method=method.upper(),
					status_code=exc.code,
					attempts=attempt,
					response_body=error_body,
				)

				if exc.code in self.config.retry_on_status and attempt < total_attempts:
					self._wait_before_retry(attempt)
					continue

				break

			except (URLError, TimeoutError, ValueError, TypeError, json.JSONDecodeError) as exc:
				last_error = RequestError(
					message=f'Network or parsing error during request: {exc}',
					url=request_url,
					method=method.upper(),
					attempts=attempt,
				)
				if attempt < total_attempts:
					self._wait_before_retry(attempt)
					continue
				break

		if last_error is None:
			last_error = RequestError(
				message='Request failed for unknown reason.',
				url=request_url,
				method=method.upper(),
				attempts=total_attempts,
			)

		self._log(
			f'Request failed after {last_error.attempts} attempt(s): '
			f'{last_error.method} {last_error.url} ({last_error.message})'
		)

		if raise_on_error:
			raise last_error

		return default

	def _build_url(
		self,
		base_url: str,
		params: Optional[dict[str, Any]],
		path_params: Optional[dict[str, Any]] = None,
	) -> str:
		url = base_url
		if path_params:
			placeholders = set(re.findall(r':([A-Za-z_][A-Za-z0-9_]*)', url))
			missing = sorted(name for name in placeholders if name not in path_params)
			if missing:
				raise ValueError(
					f'missing values for placeholders: {", ".join(missing)}'
				)

			for name, value in path_params.items():
				token = f':{name}'
				if token in url:
					url = url.replace(token, quote(str(value).strip(), safe=''))

		if not params:
			return url
		query_string = urlencode(params, doseq=True)
		separator = '&' if '?' in url else '?'
		return f'{url}{separator}{query_string}'

	def _decode_response(self, raw_body: bytes) -> Any:
		if not raw_body:
			return None

		decoded_text = raw_body.decode('utf-8')
		try:
			return json.loads(decoded_text)
		except json.JSONDecodeError:
			return decoded_text

	def _convert_response(
		self,
		payload: Any,
		parser: Optional[Callable[[Any], T]],
		expected_type: Optional[type[T]],
	) -> T:
		if parser is not None:
			return parser(payload)

		if expected_type is None:
			return payload

		if isinstance(payload, expected_type):
			return payload

		if hasattr(expected_type, 'from_dict') and isinstance(payload, dict):
			constructor = getattr(expected_type, 'from_dict')
			if callable(constructor):
				return constructor(payload)

		return expected_type(payload)

	def _wait_before_retry(self, attempt: int) -> None:
		delay = self.config.backoff_factor * (2 ** (attempt - 1))
		time.sleep(delay)

	def _read_error_body(self, error: HTTPError) -> Optional[str]:
		try:
			body = error.read()
			if not body:
				return None
			return body.decode('utf-8', errors='replace')
		except Exception:
			return None

	def _log(self, message: str) -> None:
		if self.logger is not None:
			self.logger(message)

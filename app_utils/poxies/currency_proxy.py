from datetime import date
from typing import Any

from .make_request import RequestClient


CURRENCY_API_URL = 'https://{period}.currency-api.pages.dev/v1/currencies'


def fetch_currencies(base_currency: str, period: str = 'latest') -> dict[str, Any]:
    """
    Fetch currencies by base code and return API response as-is.
    """
    url = CURRENCY_API_URL + '{currency}.json'
    base = (base_currency or '').strip().lower()
    if not base:
        return {'date': date.today().isoformat(), 'UNKNOWN': {'UNKNOWN': 1}}

    if period != 'latest':
        try:
            period = date.fromisoformat(period)
        except ValueError:
            return {'date': date.today().isoformat(), base: {base: 1}}

    url = CURRENCY_API_URL.format(period=period)
    client = RequestClient[dict[str, Any]]()
    response = client.request(
        url=url.format(period=period, currency=base),
        expected_type=dict,
        default={},
    )

    if not isinstance(response, dict):
        return {'date': date.today().isoformat(), base: {base: 1}}

    return response

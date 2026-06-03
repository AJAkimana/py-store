from datetime import date
from typing import Any

from .make_request import RequestClient


CURRENCY_API_URL = 'https://{period}.currency-api.pages.dev/v1/currencies'


def get_decimal_places(currency_code: str) -> int:
    """
    Get the number of decimal places for a given currency code.
    """
    # This is a simplified mapping. In a real application, you might want to use a more comprehensive list or an external library.
    currency_decimal_places = {
        'adp': 0,
        'bef': 0,
        'bhd': 3,
        'bif': 0,
        'byr': 0,
        'clf': 4,
        'clp': 0,
        'djf': 0,
        'eek': 0,
        'esp': 0,
        'gnf': 0,
        'grd': 0,
        'iqd': 3,
        'itl': 0,
        'isk': 0,
        'jod': 3,
        'jpy': 0,
        'kmf': 0,
        'krw': 0,
        'kwd': 3,
        'lyd': 3,
        'mgf': 0,
        'omr': 3,
        'pte': 1,
        'pyg': 0,
        'rwf': 0,
        'tnd': 3,
        'ugx': 0,
        'uyi': 0,
        'uyw': 4,
        'vnd': 0,
        'vuv': 0,
    }
    # Default to 2 decimal places
    return currency_decimal_places.get(currency_code.lower(), 2)


def fetch_currencies(base_currency: str, period: str = 'latest') -> dict[str, Any]:
    """
    Fetch currencies by base code and return API response as-is.
    """
    base = (base_currency or '').strip().lower()
    if not base:
        return {'date': date.today().isoformat(), 'UNKNOWN': {'UNKNOWN': 1}}

    if period != 'latest':
        try:
            period = date.fromisoformat(period)
        except ValueError:
            return {'date': date.today().isoformat(), base: {base: 1}}

    url = CURRENCY_API_URL.format(period=period) + f'/{base}.json'
    client = RequestClient[dict[str, Any]]()
    response = client.request(
        url=url,
        expected_type=dict,
        default={},
    )

    if not isinstance(response, dict):
        return {'date': date.today().isoformat(), base: {base: 1}}

    return response


def exchange_currencies(amount: float = 1, base: str = 'usd', targets: list[str] = ['usd'], period: str = 'latest') -> list[dict[str, Any]]:
    """
    Exchange amount from base currency to target currencies using fetched rates.
    """
    currency_data = fetch_currencies(base.lower(), period)
    todate = currency_data.get('date', date.today().isoformat())
    rates = currency_data.get(base.lower(), {})

    results = []
    for target in targets:
        rate = rates.get(target.lower())
        if rate is not None:
            decimal_places = get_decimal_places(target)
            results.append({
                'date': todate,
                'base': base.upper(),
                'target': target.upper(),
                'amount': round(amount, decimal_places),
                'converted_amount': round(amount * rate, decimal_places),
                'rate': round(rate, decimal_places),
            })

    return results

"""
Module for making requests to Azure API Management endpoints with consistent logging and output formatting.
"""

import json
import time
from typing import Any
from dataclasses import dataclass

import requests
import urllib3

# APIM Samples imports
from apimtypes import HTTP_VERB, SLEEP_TIME_BETWEEN_REQUESTS_MS, SUBSCRIPTION_KEY_PARAMETER_NAME, HttpStatusCode
from console import BOLD_G, BOLD_R, RESET, print_error, print_info, print_message, print_ok, print_val

# Disable SSL warnings for self-signed certificates
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


# ------------------------------
#    CLASSES
# ------------------------------


class _ApimRequestsBase:
    """
    Methods for making requests to the Azure API Management service.
    Provides single and multiple request helpers with consistent logging.

    Note: This class intentionally uses camelCase naming for methods and parameters
    to maintain consistency with API naming conventions and existing usage.
    """

    # ------------------------------
    #    CONSTRUCTOR
    # ------------------------------

    def __init__(self, url: str, apimSubscriptionKey: str | None = None, headers: dict[str, str] | None = None) -> None:
        """
        Initialize the ApimRequests object.

        Args:
            url: The base URL for the APIM endpoint.
            apimSubscriptionKey: Optional subscription key for APIM.
            headers: Optional additional headers to include in requests.
        """

        self._url = url
        self._headers: dict[str, str] = headers.copy() if headers else {}
        self.subscriptionKey = apimSubscriptionKey

        self._headers['Accept'] = 'application/json'

    # ------------------------------
    #    PROPERTIES
    # ------------------------------

    # apimSubscriptionKey
    @property
    def subscriptionKey(self) -> str | None:
        """
        Gets the APIM subscription key, if defined.

        Returns:
            str | None: The APIM subscrption key, if defined; otherwise None.
        """
        return self._subscriptionKey

    @subscriptionKey.setter
    def subscriptionKey(self, value: str | None) -> None:
        """
        Sets the APIM subscription key for the request to use.

        Args:
            value: The APIM subscription key to use or None to not use any key for the request
        """

        self._subscriptionKey = value

        if self._subscriptionKey:
            self._headers[SUBSCRIPTION_KEY_PARAMETER_NAME] = self._subscriptionKey
        else:
            # Remove subscription key from headers if it exists
            self._headers.pop(SUBSCRIPTION_KEY_PARAMETER_NAME, None)

    # headers
    @property
    def headers(self) -> dict[str, str]:
        """
        Get the HTTP headers used for requests.

        Returns:
            dict[str, str]: The headers dictionary.
        """
        return self._headers

    @headers.setter
    def headers(self, value: dict[str, str]) -> None:
        """
        Set the HTTP headers used for requests.

        Args:
            value: The new headers dictionary.
        """
        self._headers = value

    # ------------------------------
    #    PRIVATE METHODS
    # ------------------------------

    def _request(
        self,
        method: HTTP_VERB,
        path: str,
        headers: list[any] = None,
        data: any = None,
        msg: str | None = None,
        printResponse: bool = True,
    ) -> str | None:
        """
        Make a request to the Azure API Management service.

        Args:
            method: The HTTP method to use (e.g., 'GET', 'POST').
            path: The path to append to the base URL for the request.
            headers: Additional headers to include in the request.
            data: Data to include in the request body.
            printResponse: Whether to print the returned output.

        Returns:
            str | None: The JSON response as a string, or None on error.
        """

        try:
            if msg:
                print_message(msg, blank_above=True)

            # Ensure path has a leading slash
            if not path.startswith('/'):
                path = '/' + path

            url = self._url + path
            print_info(f'{method.value} {url}')

            merged_headers = self.headers.copy()

            if headers:
                merged_headers.update(headers)

            print_info(merged_headers)

            response = requests.request(method.value, url, headers=merged_headers, json=data, verify=False, timeout=30)

            content_type = response.headers.get('Content-Type')

            responseBody = None

            if content_type and 'application/json' in content_type:
                responseBody = json.dumps(response.json(), indent=4)
            else:
                responseBody = response.text

            if printResponse:
                self._print_response(response)

            return responseBody

        except requests.exceptions.RequestException as e:
            print_error(f'Error making request: {e}')
            return None

    def _multiRequest(
        self,
        method: HTTP_VERB,
        path: str,
        runs: int,
        headers: list[any] = None,
        data: any = None,
        msg: str | None = None,
        printResponse: bool = True,
        sleepMs: int | None = None,
    ) -> list[dict[str, Any]]:
        """
        Make multiple requests to the Azure API Management service.

        Args:
            method: The HTTP method to use (e.g., 'GET', 'POST').
            path: The path to append to the base URL for the request.
            runs: The number of times to run the request.
            headers: Additional headers to include in the request.
            data: Data to include in the request body.
            printResponse: Whether to print the returned output.
            sleepMs: Optional sleep time between requests in milliseconds (0 to not sleep).

        Returns:
            List of response dicts for each run.
        """

        api_runs = []

        session = requests.Session()

        merged_headers = self.headers.copy()
        if headers:
            merged_headers.update(headers)

        session.headers.update(merged_headers)

        try:
            if msg:
                print_message(msg, blank_above=True)

            # Ensure path has a leading slash
            if not path.startswith('/'):
                path = '/' + path

            url = self._url + path
            print_info(f'{method.value} {url}')

            for i in range(runs):
                print_info(f'▶️ Run {i + 1}/{runs}:')

                start_time = time.time()
                response = session.request(method.value, url, json=data, verify=False)
                response_time = time.time() - start_time
                print_info(f'⌚ {response_time:.2f} seconds')

                if printResponse:
                    self._print_response(response)
                else:
                    self._print_response_code(response)

                content_type = response.headers.get('Content-Type')

                if content_type and 'application/json' in content_type:
                    resp_data = json.dumps(response.json(), indent=4)
                else:
                    resp_data = response.text

                api_runs.append(
                    {
                        'run': i + 1,
                        'response': resp_data,
                        'status_code': response.status_code,
                        'response_time': response_time,
                        'headers': dict(response.headers),
                    }
                )

                # Sleep only between requests (not after the final run)
                if i < runs - 1:
                    if sleepMs is not None:
                        if sleepMs > 0:
                            time.sleep(sleepMs / 1000)
                    else:
                        time.sleep(SLEEP_TIME_BETWEEN_REQUESTS_MS / 1000)  # default sleep time
        finally:
            session.close()

        return api_runs


@dataclass
class SseEvent:
    event: str | None
    event_id: str | None
    data: str
    received_at_s: float


class ApimRequests(_ApimRequestsBase):
    def sseGet(
        self,
        path: str,
        *,
        msg: str | None = None,
        headers: dict[str, str] | None = None,
        max_events: int = 5,
        max_seconds: int = 20,
        connect_timeout_s: int = 10,
        read_timeout_s: int = 30,
        printResponse: bool = True,
    ) -> dict[str, Any]:
        """Connect to an SSE endpoint and read a small number of events.

        This helper is intentionally lightweight and is designed for notebooks where we
        want to observe streaming behavior (for example, APIM buffer-response on/off).

        Returns a dict with timing + captured events:
        - status_code
        - content_type
        - time_to_first_byte_s
        - time_to_first_event_s
        - events (list of SseEvent dicts)
        - raw_lines (first N lines)
        """

        if msg:
            print_message(msg, blank_above=True)

        if not path.startswith('/'):
            path = '/' + path

        url = self._url + path
        merged_headers = self.headers.copy()
        merged_headers['Accept'] = 'text/event-stream'
        if headers:
            merged_headers.update(headers)

        print_info(f'GET {url} (SSE)')
        print_info(merged_headers)

        start = time.time()
        first_byte_at: float | None = None
        first_event_at: float | None = None

        events: list[SseEvent] = []
        raw_lines: list[str] = []
        current_event: dict[str, str | None] = {'event': None, 'id': None, 'data': ''}

        def flush_event(now: float) -> None:
            nonlocal first_event_at
            data = (current_event.get('data') or '').rstrip('\n')
            if not data:
                # Ignore empty frames (heartbeats)
                current_event['event'] = None
                current_event['id'] = None
                current_event['data'] = ''
                return

            if first_event_at is None:
                first_event_at = now

            events.append(
                SseEvent(
                    event=current_event.get('event'),
                    event_id=current_event.get('id'),
                    data=data,
                    received_at_s=now - start,
                )
            )

            current_event['event'] = None
            current_event['id'] = None
            current_event['data'] = ''

        try:
            with requests.get(
                url,
                headers=merged_headers,
                verify=False,
                stream=True,
                timeout=(connect_timeout_s, read_timeout_s),
            ) as response:
                if printResponse:
                    self._print_response_code(response)

                content_type = response.headers.get('Content-Type', '')

                for line in response.iter_lines(decode_unicode=True, chunk_size=1):
                    now = time.time()

                    if first_byte_at is None:
                        first_byte_at = now

                    if now - start > max_seconds:
                        break

                    if line is None:
                        continue

                    # Keep some raw lines for debugging
                    if len(raw_lines) < 200:
                        raw_lines.append(line)

                    if line == '':
                        flush_event(now)
                        if len(events) >= max_events:
                            break
                        continue

                    # Comment heartbeat
                    if line.startswith(':'):
                        continue

                    if line.startswith('event:'):
                        current_event['event'] = line.split(':', 1)[1].strip()
                        continue

                    if line.startswith('id:'):
                        current_event['id'] = line.split(':', 1)[1].strip()
                        continue

                    if line.startswith('data:'):
                        data_part = line.split(':', 1)[1].lstrip()
                        current_event['data'] = (current_event.get('data') or '') + data_part + '\n'
                        continue

                # If stream ended naturally, try to flush the last event
                flush_event(time.time())

                return {
                    'status_code': response.status_code,
                    'content_type': content_type,
                    'time_to_first_byte_s': (first_byte_at - start) if first_byte_at else None,
                    'time_to_first_event_s': (first_event_at - start) if first_event_at else None,
                    'events': [
                        {
                            'event': e.event,
                            'id': e.event_id,
                            'data': e.data,
                            'received_at_s': e.received_at_s,
                        }
                        for e in events
                    ],
                    'raw_lines': raw_lines,
                }

        except requests.exceptions.RequestException as e:
            print_error(f'Error making SSE request: {e}')
            return {
                'error': str(e),
                'time_to_first_byte_s': (first_byte_at - start) if first_byte_at else None,
                'time_to_first_event_s': (first_event_at - start) if first_event_at else None,
                'events': [],
                'raw_lines': raw_lines,
            }

    def _print_response(self, response) -> None:
        """
        Print the response headers and body with appropriate formatting.
        """

        self._print_response_code(response)
        print_val('Response headers', response.headers, True)

        if response.status_code == HttpStatusCode.OK:
            try:
                data = json.loads(response.text)
                print_val('Response body', json.dumps(data, indent=4), True)
            except Exception:
                print_val('Response body', response.text, True)
        else:
            print_val('Response body', response.text, True)

    def _print_response_code(self, response) -> None:
        """
        Print the response status code with color formatting.
        """

        if HttpStatusCode.OK <= response.status_code < HttpStatusCode.MULTIPLE_CHOICES:
            status_code_str = f'{BOLD_G}{response.status_code} - {response.reason}{RESET}'
        elif response.status_code >= HttpStatusCode.BAD_REQUEST:
            status_code_str = f'{BOLD_R}{response.status_code} - {response.reason}{RESET}'
        else:
            status_code_str = str(response.status_code)

        print_val('Response status', status_code_str)

    def _poll_async_operation(self, location_url: str, headers: dict = None, timeout: int = 60, poll_interval: int = 2) -> requests.Response | None:
        """
        Poll an async operation until completion.

        Args:
            location_url: The URL from the Location header
            headers: Headers to include in polling requests
            timeout: Maximum time to wait in seconds
            poll_interval: Time between polls in seconds

        Returns:
            The final response when operation completes or None on error
        """
        start_time = time.time()

        while time.time() - start_time < timeout:
            try:
                print_info(f'GET {location_url}', True)
                print_info(headers)
                response = requests.get(location_url, headers=headers or {}, verify=False, timeout=30)

                print_info(f'Polling operation - Status: {response.status_code}')

                if response.status_code == HttpStatusCode.OK:
                    print_ok('Async operation completed successfully!')
                    return response

                if response.status_code == HttpStatusCode.ACCEPTED:
                    print_info(f'Operation still in progress, waiting {poll_interval} seconds...')
                    time.sleep(poll_interval)
                else:
                    print_error(f'Unexpected status code during polling: {response.status_code}')
                    return response

            except requests.exceptions.RequestException as e:
                print_error(f'Error polling operation: {e}')
                return None

        print_error(f'Async operation timeout reached after {timeout} seconds')
        return None

    # ------------------------------
    #    PUBLIC METHODS
    # ------------------------------

    def singleGet(self, path: str, headers=None, msg: str | None = None, printResponse: bool = True) -> Any:
        """
        Make a GET request to the Azure API Management service.

        Args:
            path: The path to append to the base URL for the request.
            headers: Additional headers to include in the request.
            printResponse: Whether to print the returned output.

        Returns:
            str | None: The JSON response as a string, or None on error.
        """

        return self._request(method=HTTP_VERB.GET, path=path, headers=headers, msg=msg, printResponse=printResponse)

    def singlePost(self, path: str, *, headers=None, data=None, msg: str | None = None, printResponse: bool = True) -> Any:
        """
        Make a POST request to the Azure API Management service.

        Args:
            path: The path to append to the base URL for the request.
            headers: Additional headers to include in the request.
            data: Data to include in the request body.
            printResponse: Whether to print the returned output.

        Returns:
            str | None: The JSON response as a string, or None on error.
        """

        return self._request(
            method=HTTP_VERB.POST,
            path=path,
            headers=headers,
            data=data,
            msg=msg,
            printResponse=printResponse,
        )

    def multiGet(
        self,
        path: str,
        runs: int,
        headers=None,
        data=None,
        msg: str | None = None,
        printResponse: bool = True,
        sleepMs: int | None = None,
    ) -> list[dict[str, Any]]:
        """
        Make multiple GET requests to the Azure API Management service.

        Args:
            path: The path to append to the base URL for the request.
            runs: The number of times to run the GET request.
            headers: Additional headers to include in the request.
            data: Data to include in the request body.
            printResponse: Whether to print the returned output.
            sleepMs: Optional sleep time between requests in milliseconds (0 to not sleep).

        Returns:
            List of response dicts for each run.
        """

        return self._multiRequest(
            method=HTTP_VERB.GET,
            path=path,
            runs=runs,
            headers=headers,
            data=data,
            msg=msg,
            printResponse=printResponse,
            sleepMs=sleepMs,
        )

    def singlePostAsync(
        self,
        path: str,
        *,
        headers=None,
        data=None,
        msg: str | None = None,
        printResponse=True,
        timeout=60,
        poll_interval=2,
    ) -> Any:
        """
        Make an async POST request to the Azure API Management service and poll until completion.

        Args:
            path: The path to append to the base URL for the request.
            headers: Additional headers to include in the request.
            data: Data to include in the request body.
            msg: Optional message to display.
            printResponse: Whether to print the returned output.
            timeout: Maximum time to wait for completion in seconds.
            poll_interval: Time between polls in seconds.

        Returns:
            str | None: The JSON response as a string, or None on error.
        """

        try:
            if msg:
                print_message(msg, blank_above=True)

            # Ensure path has a leading slash
            if not path.startswith('/'):
                path = '/' + path

            url = self._url + path
            print_info(f'POST {url}')

            merged_headers = self.headers.copy()

            if headers:
                merged_headers.update(headers)

            print_info(merged_headers)

            # Make the initial async request
            response = requests.request(HTTP_VERB.POST.value, url, headers=merged_headers, json=data, verify=False, timeout=30)

            print_info(f'Initial response status: {response.status_code}')

            if response.status_code == HttpStatusCode.ACCEPTED:  # Accepted - async operation started
                location_header = response.headers.get('Location')

                if location_header:
                    print_info(f'Found Location header: {location_header}')

                    # Poll the location URL until completion
                    final_response = self._poll_async_operation(location_header, timeout=timeout, poll_interval=poll_interval)

                    if final_response and final_response.status_code == HttpStatusCode.OK:
                        if printResponse:
                            self._print_response(final_response)

                        content_type = final_response.headers.get('Content-Type')
                        responseBody = None

                        if content_type and 'application/json' in content_type:
                            responseBody = json.dumps(final_response.json(), indent=4)
                        else:
                            responseBody = final_response.text

                        return responseBody

                    print_error('Async operation failed or timed out')
                    return None

                print_error('No Location header found in 202 response')
                if printResponse:
                    self._print_response(response)
                return None

            # Non-async response, handle normally
            if printResponse:
                self._print_response(response)

            content_type = response.headers.get('Content-Type')
            responseBody = None

            if content_type and 'application/json' in content_type:
                responseBody = json.dumps(response.json(), indent=4)
            else:
                responseBody = response.text

            return responseBody

        except requests.exceptions.RequestException as e:
            print_error(f'Error making request: {e}')
            return None

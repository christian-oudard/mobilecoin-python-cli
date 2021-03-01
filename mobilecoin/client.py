from functools import lru_cache
import http
import json

import requests

DEFAULT_URL = 'http://127.0.0.1:9090/wallet'


class Client:

    def __init__(self, url=DEFAULT_URL, verbose=False):
        self.url = url
        self.verbose = verbose

    def _req(self, request_data):
        request_data.update({
            "jsonrpc": "2.0",
            "api_version": "2",
            "id": 1
        })

        if self.verbose:
            print('POST', self.url)
            print(json.dumps(request_data, indent=4))
            print()

        try:
            r = requests.post(self.url, json=request_data)
        except requests.ConnectionError:
            # print(f'Could not connect to server at {self.url}. Try running ./mobilecoin start')
            raise

        try:
            response_data = r.json()
        except ValueError:
            print('API Error:', r.text)
            exit(1)

        if self.verbose:
            print(r.status_code, http.client.responses[r.status_code])
            print(json.dumps(response_data, indent=4))
            print()

        return response_data

    def create_account(self, name, block=None):
        params = {"name": name}
        if block is not None:
            params["first_block_index"] = str(int(block))
        return self._req({
            "method": "create_account",
            "params": params,
        })

    def import_account(self, name, entropy, block=None):
        params = {
            "entropy": entropy,
            "name": name
        }
        if block is not None:
            params["first_block_index"] = str(int(block))

        return self._req({
            "method": "import_account",
            "params": params,
        })

    @lru_cache
    def get_all_accounts(self):
        return self._req({"method": "get_all_accounts"})

    @lru_cache
    def get_account(self):
        return self._req({"method": "get_all_accounts"})

    def balance(self, account_id):
        return self._req({
            "method": "get_balance_for_account",
            "params": {
                "account_id": account_id,
            }
        })

    def delete_account(self, account_id):
        return self._req({
            "method": "delete_account",
            "params": {
                "account_id": account_id,
            }
        })

    def transactions(self, account_id):
        return self._req({
            "method": "get_all_txos_by_account",
            "params": {
                "account_id": account_id
            }
        })

    def send(self, from_account_id, to_address, amount):
        self._req({
            "method": "send_transaction",
            "params": {
                "account_id": from_account_id,
                "recipient_public_address": to_address,
                "value": amount,
            }
        })


def mob2pmob(x):
    """ Convert from MOB to picoMOB. """
    return int(float(x) * 1e12)


def pmob2mob(x):
    """ Convert from picoMOB to MOB. """
    return int(x) / 1e12

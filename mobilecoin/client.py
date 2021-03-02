from decimal import Decimal
import http
import json

import requests

DEFAULT_URL = 'http://127.0.0.1:9090/wallet'


class Client:

    def __init__(self, url=DEFAULT_URL, verbose=False):
        self.url = url
        self.verbose = verbose

    def _req(self, request_data):
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

    def _req_v1(self, request_data):
        return self._req(request_data)

    def _req_v2(self, request_data):
        default_params = {
            "jsonrpc": "2.0",
            "api_version": "2",
            "id": 1,
        }
        return self._req({**default_params, **request_data})

    def create_account(self, name, block=None):
        params = {"name": name}
        if block is not None:
            params["first_block_index"] = str(int(block))
        return self._req_v2({
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

        return self._req_v2({
            "method": "import_account",
            "params": params,
        })

    def get_all_accounts(self):
        return self._req_v2({"method": "get_all_accounts"})

    def get_account(self, account_id):
        return self._req_v2({
            "method": "get_account",
            "params": {
                "account_id": account_id,
            }
        })

    def update_account_name(self, account_id, name):
        return self._req_v2({
            "method": "update_account_name",
            "params": {
                "account_id": account_id,
                "name": name,
            }
        })

    def balance(self, account_id):
        return self._req_v2({
            "method": "get_balance_for_account",
            "params": {
                "account_id": account_id,
            }
        })

    def delete_account(self, account_id):
        return self._req_v2({
            "method": "delete_account",
            "params": {
                "account_id": account_id,
            }
        })

    def get_all_txos_by_account(self, account_id):
        return self._req_v2({
            "method": "get_all_txos_by_account",
            "params": {
                "account_id": account_id
            }
        })

    def send_transaction(self, from_account_id, amount, to_address):
        amount = str(mob2pmob(Decimal(amount)))
        self._req_v1({
            "method": "send_transaction",
            "params": {
                "account_id": from_account_id,
                "value": amount,
                "recipient_public_address": to_address,
            }
        })


def mob2pmob(x):
    """ Convert from MOB to picoMOB. """
    return round(Decimal(x) * Decimal('1e12'))


def pmob2mob(x):
    """ Convert from picoMOB to MOB. """
    return Decimal(x) / Decimal('1e12')

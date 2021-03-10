from decimal import Decimal
import http
import json

import requests

DEFAULT_URL = 'http://127.0.0.1:9090/wallet'


class WalletAPIError(Exception):
    pass


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
            print(f'Could not connect to server at {self.url}.')
            raise

        try:
            response_data = r.json()
        except ValueError:
            print('API returned invalid JSON:', r.text)
            raise

        if self.verbose:
            print(r.status_code, http.client.responses[r.status_code])
            print(json.dumps(response_data, indent=4))
            print()

        # Check for errors and unwrap result.
        try:
            result = response_data['result']
        except KeyError:
            raise WalletAPIError(json.dumps(response_data, indent=4))

        return result

    def _req_v1(self, request_data):
        return self._req(request_data)

    def _req_v2(self, request_data):
        default_params = {
            "jsonrpc": "2.0",
            "api_version": "2",
            "id": 1,
        }
        return self._req({**default_params, **request_data})

    def create_account(self, name=None, block=None):
        params = {"name": name}
        if block is not None:
            params["first_block_index"] = str(int(block))
        r = self._req_v2({
            "method": "create_account",
            "params": params
        })
        return r['account']

    def import_account(self, entropy, name=None, block=None):
        params = {
            "entropy": entropy,
        }
        if name is not None:
            params["name"] = name
        if block is not None:
            params["first_block_index"] = str(int(block))

        r = self._req_v2({
            "method": "import_account",
            "params": params
        })
        return r['account']

    def get_all_accounts(self):
        r = self._req_v2({"method": "get_all_accounts"})
        return r['account_map']

    def get_account(self, account_id):
        r = self._req_v2({
            "method": "get_account",
            "params": {"account_id": account_id}
        })
        return r['account']

    def update_account_name(self, account_id, name):
        r = self._req_v2({
            "method": "update_account_name",
            "params": {
                "account_id": account_id,
                "name": name,
            }
        })
        return r['account']

    def delete_account(self, account_id):
        return self._req_v2({
            "method": "delete_account",
            "params": {"account_id": account_id}
        })

    def export_account_secrets(self, account_id):
        r = self._req_v2({
            "method": "export_account_secrets",
            "params": {"account_id": account_id}
        })
        return r['account_secrets']

    def get_all_txos_for_account(self, account_id):
        return self._req_v2({
            "method": "get_all_txos_by_account",
            "params": {"account_id": account_id}
        })

    def get_balance_for_account(self, account_id):
        r = self._req_v2({
            "method": "get_balance_for_account",
            "params": {
                "account_id": account_id,
            }
        })
        return r['balance']

    ####

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

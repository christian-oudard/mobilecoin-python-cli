from decimal import Decimal
import http
import json

import requests

DEFAULT_URL = 'http://127.0.0.1:9090/wallet'
TRANSACTION_FEE = Decimal('0.01')


class WalletAPIError(Exception):
    pass


class Client:

    def __init__(self, url=DEFAULT_URL, verbose=False):
        self.url = url
        self.verbose = verbose

    def _req(self, request_data):
        default_params = {
            "jsonrpc": "2.0",
            "api_version": "2",
            "id": 1,
        }
        request_data = {**default_params, **request_data}

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

    def create_account(self, name=None, block=None):
        params = {"name": name}
        if block is not None:
            params["first_block_index"] = str(int(block))
        r = self._req({
            "method": "create_account",
            "params": params
        })
        return r['account']

    def import_account(self, entropy, name=None, block=None, fog_keys=None):
        params = {
            "entropy": entropy,
        }
        if name is not None:
            params["name"] = name
        if block is not None:
            params["first_block_index"] = str(int(block))
        if fog_keys is not None:
            params.update(fog_keys)
        r = self._req({
            "method": "import_account",
            "params": params
        })
        return r['account']

    def get_all_accounts(self):
        r = self._req({"method": "get_all_accounts"})
        return r['account_map']

    def get_account(self, account_id):
        r = self._req({
            "method": "get_account",
            "params": {"account_id": account_id}
        })
        return r['account']

    def update_account_name(self, account_id, name):
        r = self._req({
            "method": "update_account_name",
            "params": {
                "account_id": account_id,
                "name": name,
            }
        })
        return r['account']

    def remove_account(self, account_id):
        return self._req({
            "method": "remove_account",
            "params": {"account_id": account_id}
        })

    def export_account_secrets(self, account_id):
        r = self._req({
            "method": "export_account_secrets",
            "params": {"account_id": account_id}
        })
        return r['account_secrets']

    def get_all_txos_for_account(self, account_id):
        r = self._req({
            "method": "get_all_txos_for_account",
            "params": {"account_id": account_id}
        })
        return r['txo_map']

    def get_balance_for_account(self, account_id):
        r = self._req({
            "method": "get_balance_for_account",
            "params": {
                "account_id": account_id,
            }
        })
        return r['balance']

    def build_and_submit_transaction(self, account_id, amount, to_address):
        amount = str(mob2pmob(Decimal(amount)))
        r = self._req({
            "method": "build_and_submit_transaction",
            "params": {
                "account_id": account_id,
                "value_pmob": amount,
                "recipient_public_address": to_address,
            }
        })
        return r['transaction_log']


def mob2pmob(x):
    """ Convert from MOB to picoMOB. """
    return round(Decimal(x) * Decimal('1e12'))


def pmob2mob(x):
    """ Convert from picoMOB to MOB. """
    return Decimal(x) / Decimal('1e12')

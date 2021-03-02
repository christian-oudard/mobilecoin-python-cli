import argparse
import json
import os
from pathlib import Path
import subprocess

from mobilecoin.client import (
    Client,
    pmob2mob,
    mob2pmob,

)

NETWORK = 'testnet'
assert NETWORK in ['testnet', 'mainnet']
MC_DATA = Path.home() / '.mobilecoin' / NETWORK
LOG_LOCATION = MC_DATA / 'wallet_server_log.txt'


class CommandLineInterface:

    def main(self):
        parser = self._parser()
        args = parser.parse_args()
        args = vars(args)
        command = args.pop('command')
        if command is None:
            parser.print_help()
            exit(1)

        self.verbose = args.pop('verbose')
        self.client = Client(verbose=self.verbose)

        # Dispatch command.
        setattr(self, 'import', self.import_)  # Can't name a function "import".
        command_func = getattr(self, command)
        command_func(**args)

    def _parser(self):
        parser = argparse.ArgumentParser(
            prog='mobilecoin',
            description='MobileCoin command-line wallet.',
        )
        parser.add_argument('-v', '--verbose', action='store_true', help='Show more information.')

        subparsers = parser.add_subparsers(dest='command', help='Commands')

        start_args = subparsers.add_parser('start', help='Start the local MobileCoin wallet server.')
        start_args.add_argument('--offline', action='store_true', help='Start in offline mode.')
        start_args.add_argument('--bg', action='store_true',
                                help='Start server in the background, stop with "mobilecoin stop".')

        subparsers.add_parser('stop', help='Stop the local MobileCoin wallet server.')

        create_args = subparsers.add_parser('create', help='Create a new account.')
        create_args.add_argument('name', help='Account name.')
        create_args.add_argument('-b', '--block', type=int,
                                 help='Block index at which to start the account. No transactions before this block will be loaded.')

        import_args = subparsers.add_parser('import', help='Import an account.')
        import_args.add_argument('-b', '--block', type=int,
                                 help='Block index at which to start the account. No transactions before this block will be loaded.')
        import_args.add_argument('name', help='Account name.')
        import_args.add_argument('entropy', help='Secret root entropy.')

        delete_args = subparsers.add_parser('delete', help='Delete an account from local storage.')
        delete_args.add_argument('account_id', help='Account ID code.')

        subparsers.add_parser('list', help='List accounts.')

        show_secrets_args = subparsers.add_parser('show_secrets', help='Show account secrets.')
        show_secrets_args.add_argument('account_id', help='Account ID code.')

        transactions_args = subparsers.add_parser('transactions', help='List account transactions.')
        transactions_args.add_argument('account_id', help='Account ID code.', nargs='?')

        send_args = subparsers.add_parser('send', help='Send a transaction.')
        send_args.add_argument('amount', help='Amount of MOB to send.', type=float)
        send_args.add_argument('from_account_id', help='Account ID to send from.')
        send_args.add_argument('to_address', help='Address to send to.')

        return parser

    def _load_account_prefix(self, prefix):
        response = self.client.get_all_accounts()
        account_ids = response['result']['account_ids']
        matching_ids = [
            a_id for a_id in account_ids
            if a_id.startswith(prefix)
        ]
        if len(matching_ids) == 0:
            print('Could not find account starting with', prefix)
            exit(1)
        elif len(matching_ids) == 1:
            account_id = matching_ids[0]
            return response['result']['account_map'][account_id]
        else:
            print('Multiple matching matching ids: {}'.format(', '.join(matching_ids)))
            exit(1)

    def start(self, offline=False, bg=False):
        if NETWORK == 'testnet':
            wallet_server_command = ['./full-service-testnet']
        elif NETWORK == 'mainnet':
            wallet_server_command = ['./full-service-mainnet']

        wallet_server_command += [
            '--wallet-db', str(MC_DATA / 'wallet-db/encrypted-wallet.db'),
            '--ledger-db', str(MC_DATA / 'ledger-db'),
        ]
        if offline:
            wallet_server_command += [
                '--offline',
            ]
        else:
            if NETWORK == 'testnet':
                wallet_server_command += [
                    '--peer mc://node1.test.mobilecoin.com/',
                    '--peer mc://node2.test.mobilecoin.com/',
                    '--tx-source-url https://s3-us-west-1.amazonaws.com/mobilecoin.chain/node1.test.mobilecoin.com/',
                    '--tx-source-url https://s3-us-west-1.amazonaws.com/mobilecoin.chain/node2.test.mobilecoin.com/',
                ]
            elif NETWORK == 'mainnet':
                wallet_server_command += [
                    '--peer', 'mc://node1.prod.mobilecoinww.com/',
                    '--peer', 'mc://node2.prod.mobilecoinww.com/',
                    '--tx-source-url', 'https://ledger.mobilecoinww.com/node1.prod.mobilecoinww.com/',
                    '--tx-source-url', 'https://ledger.mobilecoinww.com/node2.prod.mobilecoinww.com/',
                ]
        if bg:
            wallet_server_command += [
                '>', str(LOG_LOCATION), '2>&1'
            ]

        if NETWORK == 'testnet':
            print('Starting TestNet wallet server...')
        elif NETWORK == 'mainnet':
            print('Starting MobileCoin wallet server...')

        if self.verbose:
            print(' '.join(wallet_server_command))

        MC_DATA.mkdir(parents=True, exist_ok=True)
        (MC_DATA / 'ledger-db').mkdir(exist_ok=True)
        (MC_DATA / 'wallet-db').mkdir(exist_ok=True)

        os.environ['RUST_LOG'] = 'info'
        os.environ['mc_ledger_sync'] = 'info'
        if bg:
            subprocess.Popen(' '.join(wallet_server_command), shell=True)
            print('Started, view log at {}.'.format(LOG_LOCATION))
            print('Stop server with "mobilecoin stop".')
        else:
            subprocess.run(' '.join(wallet_server_command), shell=True)

    def stop(self):
        if self.verbose:
            print('Stopping MobileCoin wallet server...')
        if NETWORK == 'testnet':
            subprocess.Popen(['killall', '-v', 'full-service-testnet'])
        elif NETWORK == 'mainnet':
            subprocess.Popen(['killall', '-v', 'full-service'])

    def create(self, **args):
        response = self.client.create_account(**args)
        account = response['result']['account']
        account_id = account['account_id']
        print('Created a new account.')
        print(account_id[:6], account['name'])

    def import_(self, **args):
        response = self.client.import_account(**args)
        account = response['result']['account']
        account_id = account['account_id']
        print('Imported account.')
        print(account_id[:6], account['name'])

    def delete(self, account_id):
        account = self._load_account_prefix(account_id)
        account_id = account['account_id']

        confirmation = input('\n'.join([
            'This will delete all stored information for the account "{}",'.format(account['name']),
            'account id {}'.format(account_id[:6]),
            'You will lose access to the funds in this account unless you',
            'restore it from the root entropy. Continue? (Y/N) '
        ]))
        if confirmation.lower() not in ['y', 'yes']:
            print('Cancelled.')
            return

        self.client.delete_account(account_id)
        print('Deleted.')

    def list(self, **args):
        response = self.client.get_all_accounts(**args)
        accounts = response['result']['account_map']
        if len(accounts) == 0:
            print('No accounts.')
            return

        for account_id, account in accounts.items():
            # Show basic information.
            print()
            print(account_id[:6], account['name'])
            print('  address', account['main_address'])

            # Show balance.
            response = self.client.balance(account['account_id'])
            balance = response['result']['balance']

            total_blocks = int(balance['network_block_count'])
            offline = (total_blocks == 0)
            if offline:
                total_blocks = balance['local_block_count']

            print('  {} MOB ({}/{} blocks synced) {}'.format(
                pmob2mob(balance['unspent_pmob']),
                balance['account_block_count'],
                total_blocks,
                ' [offline]' if offline else '',
            ))

        print()

    def history(self, account_id):
        pass

    def show_secrets(self, account_id):
        account = self._load_account_prefix(account_id)
        account_id = account['account_id']

        confirmation = input('\n'.join([
            'You are about to view the secret keys for the account "{}",'.format(account['name']),
            'account id {}'.format(account_id[:6]),
            'Anyone who can see these keys can spend all the funds in your account. It is recommended to be',
            'somewhere private and with no cameras. Continue? (Y/N) '
        ]))
        if confirmation.lower() not in ['y', 'yes']:
            print('Cancelled.')
            return

        print()
        print(account_id[:6], account['name'])
        print('  Root Entropy:', account['entropy'])
        print('  View Private Key:', account['account_key']['view_private_key'])
        print('  Spend Private Key:', account['account_key']['spend_private_key'])

    def send(self, account_id, address, amount):
        amount = str(mob2pmob(amount))
        pass

    def prepare():
        pass

    def submit():
        pass

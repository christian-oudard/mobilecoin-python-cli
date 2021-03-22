import argparse
from decimal import Decimal
import json
import os
from pathlib import Path
import subprocess

from mnemonic import Mnemonic
import segno

from .utility import (
    pmob2mob,
    TRANSACTION_FEE,
)
from .client import Client


config = json.loads(os.environ['MOBILECOIN_CONFIG'])


class CommandLineInterface:

    def __init__(self):
        self.verbose = False

    def main(self):
        self._create_parsers()

        args = self.parser.parse_args()
        args = vars(args)
        command = args.pop('command')
        if command is None:
            self.parser.print_help()
            exit(1)

        self.verbose = args.pop('verbose')
        self.client = Client(verbose=self.verbose)

        # Dispatch command.
        setattr(self, 'import', self.import_)  # Can't name a function "import".
        command_func = getattr(self, command)
        command_func(**args)

    def _create_parsers(self):
        self.parser = argparse.ArgumentParser(
            prog='mobilecoin',
            description='MobileCoin command-line wallet.',
        )
        self.parser.add_argument('-v', '--verbose', action='store_true', help='Show more information.')

        subparsers = self.parser.add_subparsers(dest='command', help='Commands')

        self.start_args = subparsers.add_parser('start', help='Start the local MobileCoin wallet server.')
        self.start_args.add_argument('--offline', action='store_true', help='Start in offline mode.')
        self.start_args.add_argument('--bg', action='store_true',
                                     help='Start server in the background, stop with "mobilecoin stop".')

        self.stop_args = subparsers.add_parser('stop', help='Stop the local MobileCoin wallet server.')

        self.create_args = subparsers.add_parser('create', help='Create a new account.')
        self.create_args.add_argument('-n', '--name', help='Account name.')
        self.create_args.add_argument('-b', '--block', type=int,
                                      help='Block index at which to start the account. No transactions before this block will be loaded.')

        self.rename_args = subparsers.add_parser('rename', help='Change account name.')
        self.rename_args.add_argument('account_id', help='Account ID code.')
        self.rename_args.add_argument('name', help='New account name.')

        self.import_args = subparsers.add_parser('import', help='Import an account.')
        self.import_args.add_argument('seed', help='Account seed phrase, seed file, or root entropy hex.')
        self.import_args.add_argument('-n', '--name', help='Account name.')
        self.import_args.add_argument('-b', '--block', type=int,
                                      help='Block index at which to start the account. No transactions before this block will be loaded.')

        self.export_args = subparsers.add_parser('export', help='Export seed phrase.')
        self.export_args.add_argument('account_id', help='Account ID code.')

        self.qr_args = subparsers.add_parser('qr', help='Show account address as a QR code')
        self.qr_args.add_argument('account_id', help='Account ID code.')

        self.remove_args = subparsers.add_parser('remove', help='Remove an account from local storage.')
        self.remove_args.add_argument('account_id', help='Account ID code.')

        self.list_args = subparsers.add_parser('list', help='List accounts.')

        self.history_args = subparsers.add_parser('history', help='Show account transaction history.')
        self.history_args.add_argument('account_id', help='Account ID code.')

        self.send_args = subparsers.add_parser('send', help='Send a transaction.')
        self.send_args.add_argument('--build-only', action='store_true', help='Just build the transaction, do not submit it.')
        self.send_args.add_argument('account_id', help='Account ID to send from.')
        self.send_args.add_argument('amount', help='Amount of MOB to send.')
        self.send_args.add_argument('to_address', help='Address to send to.')

    def _load_account_prefix(self, prefix):
        accounts = self.client.get_all_accounts()
        matching_ids = [
            a_id for a_id in accounts.keys()
            if a_id.startswith(prefix)
        ]
        if len(matching_ids) == 0:
            print('Could not find account starting with', prefix)
            exit(1)
        elif len(matching_ids) == 1:
            account_id = matching_ids[0]
            return accounts[account_id]
        else:
            print('Multiple matching matching ids: {}'.format(', '.join(matching_ids)))
            exit(1)

    def start(self, offline=False, bg=False):
        wallet_server_command = [
            config['executable'],
            '--ledger-db', config['ledger-db'],
            '--wallet-db', config['wallet-db'],
        ]
        if offline:
            wallet_server_command += ['--offline']
        else:
            for peer in config['peer']:
                wallet_server_command += ['--peer', peer]
            for tx_source_url in config['tx-source-url']:
                wallet_server_command += ['--tx-source-url', tx_source_url]

        ingest_enclave = config.get('fog-ingest-enclave-css')
        if ingest_enclave is not None:
            wallet_server_command += ['--fog-ingest-enclave-css', ingest_enclave]

        if bg:
            wallet_server_command += [
                '>', config['logfile'], '2>&1'
            ]

        if self.verbose:
            print(' '.join(wallet_server_command))

        print('Starting {}...'.format(Path(config['executable']).name))

        Path(config['ledger-db']).mkdir(parents=True, exist_ok=True)
        Path(config['wallet-db']).parent.mkdir(parents=True, exist_ok=True)

        if bg:
            subprocess.Popen(' '.join(wallet_server_command), shell=True)
            print('Started, view log at {}.'.format(config['logfile']))
            print('Stop server with "mobcli stop".')
        else:
            subprocess.run(' '.join(wallet_server_command), shell=True)

    def stop(self):
        if self.verbose:
            print('Stopping MobileCoin wallet server...')
        subprocess.Popen(['killall', '-v', config['executable']])

    def create(self, **args):
        account = self.client.create_account(**args)
        print('Created a new account.')
        print()
        _print_account(account)
        print()

    def rename(self, account_id, name):
        account = self._load_account_prefix(account_id)
        old_name = account['name']
        account_id = account['account_id']
        account = self.client.update_account_name(account_id, name)
        print('Renamed account from "{}" to "{}".'.format(
            old_name,
            account['name'],
        ))
        print()
        _print_account(account)
        print()

    def import_(self, seed, **args):
        entropy, block, fog_keys = _load_import(seed)
        if args['block'] is None and block is not None:
            args['block'] = block
        account = self.client.import_account(entropy, fog_keys=fog_keys, **args)
        account_id = account['account_id']
        balance = self.client.get_balance_for_account(account_id)

        print('Imported account.')
        print()
        _print_account(account, balance)
        print()

    def export(self, account_id):
        account = self._load_account_prefix(account_id)
        account_id = account['account_id']
        balance = self.client.get_balance_for_account(account_id)

        print('You are about to export the seed phrase for this account:')
        print()
        _print_account(account, balance)
        print()
        print('Keep the exported seed phrase file safe and private!')
        print('Anyone who has access to the seed phrase can spend all the')
        print('funds in the account.')
        if not confirm('Really write account seed phrase to a file? (Y/N) '):
            print('Cancelled.')
            return

        secrets = self.client.export_account_secrets(account_id)
        filename = 'mobilecoin_seed_phrase_{}.json'.format(account_id[:16])
        try:
            _save_export(account, secrets, filename)
        except OSError as e:
            print('Could not write file: {}'.format(e))
            exit(1)
        else:
            print(f'Wrote {filename}.')

    def qr(self, account_id):
        account = self._load_account_prefix(account_id)
        account_id = account['account_id']
        balance = self.client.get_balance_for_account(account_id)

        mob_url = 'mob:///b58/{}'.format(account['main_address'])
        qr = segno.make(mob_url)
        qr.terminal()

        print()
        _print_account(account, balance)
        print()

    def remove(self, account_id):
        account = self._load_account_prefix(account_id)
        account_id = account['account_id']
        balance = self.client.get_balance_for_account(account_id)

        print('You are about to remove this account:')
        print()
        _print_account(account, balance)
        print()
        print('You will lose access to the funds in this account unless you')
        print('restore it from the seed phrase.')
        if not confirm('Continue? (Y/N) '):
            print('Cancelled.')
            return

        self.client.remove_account(account_id)
        print('Removed.')

    def list(self, **args):
        accounts = self.client.get_all_accounts(**args)

        if len(accounts) == 0:
            print('No accounts.')
            return

        account_list = []
        for account_id, account in accounts.items():
            balance = self.client.get_balance_for_account(account_id)
            account_list.append((account_id, account, balance))

        for (account_id, account, balance) in account_list:
            total_blocks = int(balance['network_block_index'])
            offline = (total_blocks == 0)
            if offline:
                total_blocks = balance['local_block_index']
            print()
            _print_account(account, balance)

        print()

    def send(self, account_id, amount, to_address, build_only=False):
        account = self._load_account_prefix(account_id)
        account_id = account['account_id']
        balance = self.client.get_balance_for_account(account_id)
        unspent = pmob2mob(balance['unspent_pmob'])

        if amount == "all":
            amount = unspent - TRANSACTION_FEE
            total_amount = unspent
        else:
            amount = Decimal(amount)
            total_amount = amount + TRANSACTION_FEE

        if build_only:
            verb = 'Building transaction for'
        else:
            verb = 'Sending'

        print('\n'.join([
            '{} {} from account {} {}',
            'to address {}.',
            'Fee is {}, for a total amount of {}.',
        ]).format(
            verb,
            _format_mob(amount),
            account_id[:6],
            account['name'],
            to_address,
            _format_mob(TRANSACTION_FEE),
            _format_mob(total_amount),
        ))

        if total_amount > unspent:
            print('\n'.join([
                'Cannot send this transaction, because the account only',
                'contains {:.4f} MOB. Try sending all funds by entering amount as "all".',
            ]).format(unspent))
            return

        if build_only:
            tx_proposal = self.client.build_transaction(account_id, amount, to_address)
            path = Path('tx_proposal.json')
            if path.exists():
                print(f'{path} already exists.')
            else:
                with path.open('w') as f:
                    json.dump(tx_proposal, f)
                print(f'Wrote {path}')
            return

        if not confirm('Confirm? (Y/N) '):
            print('Cancelled.')
            return

        transaction_log = self.client.build_and_submit_transaction(account_id, amount, to_address)

        print('Sent {:.4f} MOB, with a transaction fee of {:.4f} MOB'.format(
            pmob2mob(transaction_log['value_pmob']),
            pmob2mob(transaction_log['fee_pmob']),
        ))

    def history(self, account_id):
        account = self._load_account_prefix(account_id)
        account_id = account['account_id']

        transactions = self.client.get_all_transaction_logs_for_account(account_id)
        transactions = sorted(
            transactions.values(),
            key=lambda t: int(t['finalized_block_index'])
        )
        for t in transactions:
            print()
            amount = _format_mob(pmob2mob(t['value_pmob']))
            if t['direction'] == 'tx_direction_received':
                print('Received {}'.format(amount))
                print('  at {}'.format(t['assigned_address_id']))
            elif t['direction'] == 'tx_direction_sent':
                fee = _format_mob(pmob2mob(t['fee_pmob']))
                print('Sent {} (fee {})'.format(amount, fee))
                print('  to {}'.format(t['recipient_address_id']))
            print('  in block', t['finalized_block_index'])
        print()

def confirm(message):
    confirmation = input(message)
    return confirmation.lower() in ['y', 'yes']


def _format_mob(mob):
    return '{:.4f} MOB'.format(mob)


def _print_account(account, balance=None):
    account_id = account['account_id']

    print(account_id[:6], account['name'])
    print('  address', account['main_address'])

    if balance is not None:
        total_blocks = int(balance['network_block_index'])
        offline = (total_blocks == 0)
        if offline:
            total_blocks = balance['local_block_index']
        print('  {} ({}/{} blocks synced) {}'.format(
            _format_mob(pmob2mob(balance['unspent_pmob'])),
            balance['account_block_index'],
            total_blocks,
            ' [offline]' if offline else '',
        ))


def _print_txo(txo, received=False):
    print(txo)
    to_address = txo['assigned_address']
    if received:
        verb = 'Received'
    else:
        verb = 'Spent'
    print('  {} {}'.format(verb, _format_mob(pmob2mob(txo['value_pmob']))))
    if received:
        if int(txo['subaddress_index']) == 1:
            print('    as change')
        else:
            print('    at subaddress {}, {}'.format(
                txo['subaddress_index'],
                to_address,
            ))
    else:
        print('    to unknown address')


def _load_import(seed):
    # Try to use it as hexadecimal root entropy.
    try:
        b = bytes.fromhex(seed)
        if len(b) == 32:
            entropy = b.hex()
            return entropy, None, None
    except ValueError:
        pass

    # Try to interpret it as a BIP39 mnemonic.
    try:
        entropy = Mnemonic('english').to_entropy(seed).hex()
        return entropy, None, None
    except (ValueError, LookupError):
        pass

    # Try to open it as a JSON filename.
    with open(seed) as f:
        data = json.load(f)
        fog_keys = {}
        for field in [
            'fog_report_url',
            'fog_report_id',
            'fog_authority_spki',
        ]:
            value = data['account_key'].get(field)
            if value is not None:
                fog_keys[field] = value

    return (
        data['root_entropy'],
        data.get('first_block_index'),
        fog_keys,
    )


def _save_export(account, secrets, filename):
    entropy = secrets['entropy']
    seed_phrase = Mnemonic('english').to_mnemonic(bytes.fromhex(entropy))

    export_data = {
        "seed_phrase": seed_phrase,
        "root_entropy": entropy,
        "account_id": account['account_id'],
        "account_name": account['name'],
        "account_key": secrets['account_key'],
        "first_block_index": account['first_block_index'],
    }

    path = Path(filename)
    if path.exists():
        raise OSError('File exists.')

    with path.open('w') as f:
        json.dump(export_data, f, indent=4)
        f.write('\n')

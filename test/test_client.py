from contextlib import contextmanager
import sys

from mobilecoin import Client, WalletAPIError


def main():
    # c = Client(verbose=True)
    c = Client(verbose=False)

    # source_wallet_entropy = sys.argv[1]

    # Start and end with an empty wallet.
    check_wallet_empty(c)
    try:
        test_errors(c)
        test_account_management(c)
        # test_transactions(c, source_wallet_entropy)
    except Exception:
        print('FAIL')
        raise
    else:
        print('ALL PASS')
    finally:
        delete_all_accounts(c)
        check_wallet_empty(c)


def test_errors(c):
    print('test_errors')

    try:
        c.get_account('invalid')
    except WalletAPIError:
        pass
    else:
        raise AssertionError()

    print('PASS')

def test_account_management(c):
    print('test_account_management')

    # Create an account.
    account = c.create_account()
    account_id = account['account_id']

    # Get accounts.
    account_2 = c.get_account(account_id)
    assert account == account_2

    accounts = c.get_all_accounts()
    account_ids = list(accounts.keys())
    assert account_ids == [account_id]
    assert accounts[account_id] == account

    # Rename account.
    assert account['name'] == ''
    c.update_account_name(account_id, 'X')
    account = c.get_account(account_id)
    assert account['name'] == 'X'

    # Delete the created account.
    response = c.delete_account(account_id)

    # Import an account by entropy.
    entropy = '0000000000000000000000000000000000000000000000000000000000000000'
    account = c.import_account(entropy)
    account_id = account['account_id']
    assert (
        account['main_address']
        == '6UEtkm1rieLhuz2wvELPHdGiCb96zNnW856QVeGLvYzE7NhmbG1MxnoSPGqyVfEHDvxzQmaURFpZcxT9TSypVgRVAusr7svtD1TcrYj92Uh'
    )

    # Export secrets.
    secrets = c.export_account_secrets(account_id)
    assert secrets['entropy'] == entropy
    assert (
        secrets['account_key']['view_private_key']
        == '0a20b0146de8cd8f5b7962f9e74a5ef0f3e58a9550c9527ac144f38729f0fd3fed0e'
    )
    assert (
        secrets['account_key']['spend_private_key']
        == '0a20b4bf01a77ed4e065e9082d4bda67add30c88e021dcf81fc84e6a9ca2cb68e107'
    )
    c.delete_account(account_id)

    print('PASS')

def test_transactions(c, source_wallet_entropy):
    print('test_transactions')

    print(source_wallet_entropy)
    # Import an account with money.
    # account = c.import_account_by_entropy(c, source_wallet_entropy)
    # c.get_bala
    print('PASS')


def check_wallet_empty(c):
    with quiet(c):
        accounts = c.get_all_accounts()
        assert accounts == {}, 'Wallet not empty!'


def delete_all_accounts(c):
    with quiet(c):
        accounts = c.get_all_accounts()
        for account_id in accounts.keys():
            c.delete_account(account_id)


@contextmanager
def quiet(c):
    old_verbose = c.verbose
    c.verbose = False
    yield
    c.verbose = old_verbose


if __name__ == '__main__':
    main()

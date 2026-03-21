from decimal import Decimal

from .models import PlatformSettings, Wallet


def get_or_create_wallet_with_starting_coins(user, for_update=False):
    queryset = Wallet.objects
    if for_update:
        queryset = queryset.select_for_update()

    settings_obj = PlatformSettings.get_instance()
    starting_coin_balance = Decimal(settings_obj.starting_coin_balance)

    wallet, created = queryset.get_or_create(
        user=user,
        defaults={"coin_balance": starting_coin_balance},
    )
    return wallet, created

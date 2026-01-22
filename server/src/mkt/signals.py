# # signals.py (inside your markets app)




# # signals.py (inside your markets app)
# from django.db.models.signals import post_save
# from django.dispatch import receiver
# from django.core.exceptions import ObjectDoesNotExist
# from django_q.tasks import async_task
# import logging

# from .models import OptionData
# from betengine.models import Stock

# logger = logging.getLogger(__name__)

# # from django.db import transaction

# # @receiver(post_save, sender=OptionData)
# # def trigger_market_population(sender, instance, created, **kwargs):
# #     try:
# #         stock = Stock.objects.get(symbol=instance.symbol)
        
# #         # Use on_commit to ensure the transaction is successful first
# #         transaction.on_commit(
# #             lambda: async_task("mkt.tasks.populate_market_for_stock", [stock.id])
# #         )
        
# #         logger.info(f"Triggered market population for stock {stock.symbol}")
        
# #     except ObjectDoesNotExist:
# #         logger.warning(f"No Stock found for symbol {instance.symbol}. Market population skipped.")


# # from django.db.models.signals import post_save
# # from django.dispatch import receiver
# # from django_q.tasks import async_task
# # from django.core.exceptions import ObjectDoesNotExist

# # from .models import OptionData
# # from betengine.models import Stock


# # @receiver(post_save, sender=OptionData)
# # def trigger_market_population(sender, instance, created, **kwargs):
# #     """
# #     Whenever an OptionData is created or updated,
# #     trigger market population for the related stock.
# #     If OptionData only stores symbol, we resolve Stock by symbol.
# #     """
# #     try:
# #         stock = Stock.objects.get(symbol=instance.symbol)
# #         async_task("mkt.tasks.populate_market_for_stock", stock.id)
# #     except ObjectDoesNotExist:
# #         # If no stock exists for this symbol, just log or ignore
# #         print(f"[WARN] No Stock found for symbol {instance.symbol}")

# market_data/models.py
from django.contrib.auth import get_user_model
from django.db import models

User = get_user_model()


class OptionData(models.Model):
    OPTION_TYPE_CHOICES = [
        ("call", "Call"),
        ("put", "Put"),
    ]

    # Identification
    contract_id = models.CharField(max_length=50, unique=True, null=True, blank=True)
    symbol = models.CharField(max_length=10)

    # Core option details
    expiration = models.DateField(null=True, blank=True)
    strike = models.FloatField()
    option_type = models.CharField(max_length=4, choices=OPTION_TYPE_CHOICES)

    # Pricing (mark is the main price field now)
    mark = models.FloatField(null=True, blank=True)

    # Volume and open interest
    volume = models.IntegerField(null=True, blank=True)
    open_interest = models.IntegerField(null=True, blank=True)

    # Volatility and Greeks
    implied_volatility = models.FloatField(null=True, blank=True)
    delta = models.FloatField(null=True, blank=True)
    gamma = models.FloatField(null=True, blank=True)
    theta = models.FloatField(null=True, blank=True)
    vega = models.FloatField(null=True, blank=True)
    rho = models.FloatField(null=True, blank=True)

    # Metadata
    quote_date = models.DateField()  # corresponds to Alpha Vantage's "date"
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)


    def __str__(self):
        return f"{self.symbol} {self.option_type.upper()} {self.strike} {self.expiration}"


# class OptionData(models.Model):
#     OPTION_TYPE_CHOICES = [
#         ("call", "Call"),
#         ("put", "Put"),
#     ]

#     contract_id = models.CharField(max_length=50, unique=True, null=True, blank=True)
#     symbol = models.CharField(max_length=10)
    
#     # Make expiration optional to handle missing data
#     expiration = models.DateField(null=True, blank=True)
    
#     strike = models.FloatField()
#     option_type = models.CharField(max_length=4, choices=OPTION_TYPE_CHOICES)

#     # Pricing data
#     mark = models.FloatField(null=True, blank=True)
#     bid = models.FloatField(null=True, blank=True)
#     bid_size = models.IntegerField(null=True, blank=True)
#     ask = models.FloatField(null=True, blank=True)
#     ask_size = models.IntegerField(null=True, blank=True)
#     last = models.FloatField(null=True, blank=True)

#     # Volume and open interest
#     volume = models.IntegerField(null=True, blank=True)
#     open_interest = models.IntegerField(null=True, blank=True)

#     # Volatility and Greeks
#     implied_volatility = models.FloatField(null=True, blank=True)
#     delta = models.FloatField(null=True, blank=True)
#     gamma = models.FloatField(null=True, blank=True)
#     theta = models.FloatField(null=True, blank=True)
#     vega = models.FloatField(null=True, blank=True)
#     rho = models.FloatField(null=True, blank=True)

#     # Metadata
#     quote_date = models.DateField()  # Corresponds to Alpha Vantage's `date` field
#     created_at = models.DateTimeField(auto_now_add=True)

#     def __str__(self):
#         return f"{self.symbol} {self.option_type.upper()} {self.strike} {self.expiration}"
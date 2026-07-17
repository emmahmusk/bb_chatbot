from django.db import models


class MarketDocument(models.Model):
    source_id = models.CharField(max_length=64, unique=True, db_index=True)
    symbol = models.CharField(max_length=16, db_index=True)
    company_name = models.CharField(max_length=255, blank=True)
    expiry_date = models.DateField(null=True, blank=True, db_index=True)
    content = models.TextField()
    content_hash = models.CharField(max_length=64)
    payload = models.JSONField(default=dict)
    embedding = models.JSONField(default=list)
    source_updated_at = models.DateTimeField(null=True, blank=True)
    indexed_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["symbol", "expiry_date", "source_id"]

    def __str__(self):
        return f"{self.symbol} market {self.source_id}"

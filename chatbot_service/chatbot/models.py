import uuid

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


class Conversation(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    title = models.CharField(max_length=160, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True, db_index=True)

    class Meta:
        ordering = ["-updated_at"]

    def __str__(self):
        return self.title or f"Conversation {self.id}"


class ChatMessage(models.Model):
    ROLE_CHOICES = [("user", "User"), ("assistant", "Assistant")]

    conversation = models.ForeignKey(
        Conversation,
        on_delete=models.CASCADE,
        related_name="messages",
    )
    role = models.CharField(max_length=16, choices=ROLE_CHOICES)
    content = models.TextField()
    structured_answer = models.JSONField(default=dict, blank=True)
    sources = models.JSONField(default=list, blank=True)
    needs_clarification = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["created_at", "id"]
        indexes = [models.Index(fields=["conversation", "created_at"])]

    def __str__(self):
        return f"{self.role} message in {self.conversation_id}"


class BetAudit(models.Model):
    fixture_id = models.CharField(max_length=128, blank=True)
    sport = models.CharField(max_length=64, blank=True)
    league = models.CharField(max_length=128, blank=True)
    market = models.CharField(max_length=128, blank=True)
    selection = models.CharField(max_length=255, blank=True)
    chosen_sportsbook = models.CharField(max_length=128)
    chosen_price = models.FloatField(null=True, blank=True)
    chosen_decimal = models.FloatField(null=True, blank=True)
    best_sportsbook = models.CharField(max_length=128, blank=True)
    best_price = models.FloatField(null=True, blank=True)
    best_decimal = models.FloatField(null=True, blank=True)
    lowest_sportsbook = models.CharField(max_length=128, blank=True)
    lowest_decimal = models.FloatField(null=True, blank=True)
    spread_decimal = models.FloatField(null=True, blank=True)
    audit_reason = models.CharField(max_length=255, blank=True)
    edge_decimal = models.FloatField(null=True, blank=True)
    is_bad_bet = models.BooleanField(default=False, db_index=True)
    comparison_snapshot = models.JSONField(default=list, blank=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.chosen_sportsbook} audit for {self.selection}"

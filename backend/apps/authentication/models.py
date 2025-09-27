# Create your models here.
# apps/authentication/models.py
from django.contrib.auth.models import AbstractUser
from django.db import models

class Student(AbstractUser):
    student_id = models.CharField(max_length=20, unique=True)
    program = models.CharField(max_length=100, blank=True)
    year = models.IntegerField(null=True, blank=True)
    department = models.CharField(max_length=100, blank=True)
    phone = models.CharField(max_length=15, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.username} ({self.student_id})"

# apps/activities/models.py
from django.db import models
from django.contrib.auth import get_user_model
import uuid

User = get_user_model()

class ActivityType(models.TextChoices):
    CYCLING = 'cycling', 'Cycling'
    ENERGY = 'energy', 'Energy Saving'
    ASSIGNMENTS = 'assignments', 'Assignments'
    WORKSHOPS = 'workshops', 'Eco Workshops'

class ActivityStatus(models.TextChoices):
    PENDING = 'pending', 'Pending'
    APPROVED = 'approved', 'Approved'
    REJECTED = 'rejected', 'Rejected'

class Activity(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    student = models.ForeignKey(User, on_delete=models.CASCADE, related_name='activities')
    activity_type = models.CharField(max_length=20, choices=ActivityType.choices)
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    evidence_url = models.URLField(blank=True, null=True)
    evidence_note = models.TextField(blank=True)
    location = models.CharField(max_length=200, blank=True)
    
    # GPS coordinates
    start_latitude = models.DecimalField(max_digits=10, decimal_places=7, null=True, blank=True)
    start_longitude = models.DecimalField(max_digits=10, decimal_places=7, null=True, blank=True)
    end_latitude = models.DecimalField(max_digits=10, decimal_places=7, null=True, blank=True)
    end_longitude = models.DecimalField(max_digits=10, decimal_places=7, null=True, blank=True)
    
    # Activity metrics
    distance_km = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    duration_minutes = models.IntegerField(null=True, blank=True)
    energy_saved_kwh = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True)
    
    # Status and verification
    status = models.CharField(max_length=20, choices=ActivityStatus.choices, default=ActivityStatus.PENDING)
    verified_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='verified_activities')
    verification_notes = models.TextField(blank=True)
    
    # Timestamps
    activity_date = models.DateTimeField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-created_at']
        verbose_name_plural = 'Activities'
    
    def __str__(self):
        return f"{self.student.username} - {self.get_activity_type_display()} ({self.status})"

# apps/credits/models.py
from django.db import models
from django.contrib.auth import get_user_model
from apps.activities.models import Activity

User = get_user_model()

class CreditWallet(models.Model):
    student = models.OneToOneField(User, on_delete=models.CASCADE, related_name='credit_wallet')
    total_credits = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    credits_earned = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    credits_spent = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    level = models.CharField(max_length=50, default='Seed')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def calculate_level(self):
        if self.total_credits >= 200:
            return 'Forest'
        elif self.total_credits >= 120:
            return 'Grove'
        elif self.total_credits >= 60:
            return 'Sapling'
        return 'Seed'
    
    def save(self, *args, **kwargs):
        self.level = self.calculate_level()
        super().save(*args, **kwargs)
    
    def __str__(self):
        return f"{self.student.username} - {self.total_credits} credits ({self.level})"

class CreditTransaction(models.Model):
    TRANSACTION_TYPES = [
        ('earned', 'Earned'),
        ('spent', 'Spent'),
        ('bonus', 'Bonus'),
        ('penalty', 'Penalty'),
    ]
    
    wallet = models.ForeignKey(CreditWallet, on_delete=models.CASCADE, related_name='transactions')
    activity = models.ForeignKey(Activity, on_delete=models.CASCADE, null=True, blank=True)
    transaction_type = models.CharField(max_length=20, choices=TRANSACTION_TYPES)
    amount = models.DecimalField(max_digits=8, decimal_places=2)
    description = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.wallet.student.username} - {self.transaction_type} {self.amount}"

class Reward(models.Model):
    name = models.CharField(max_length=200)
    description = models.TextField()
    cost_credits = models.DecimalField(max_digits=8, decimal_places=2)
    category = models.CharField(max_length=100)
    is_active = models.BooleanField(default=True)
    max_redemptions = models.IntegerField(null=True, blank=True)
    current_redemptions = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"{self.name} ({self.cost_credits} CC)"

class RewardRedemption(models.Model):
    student = models.ForeignKey(User, on_delete=models.CASCADE, related_name='redemptions')
    reward = models.ForeignKey(Reward, on_delete=models.CASCADE, related_name='redemptions')
    credits_spent = models.DecimalField(max_digits=8, decimal_places=2)
    status = models.CharField(max_length=20, choices=[
        ('pending', 'Pending'),
        ('approved', 'Approved'),
        ('fulfilled', 'Fulfilled'),
        ('rejected', 'Rejected'),
    ], default='pending')
    redeemed_at = models.DateTimeField(auto_now_add=True)
    fulfilled_at = models.DateTimeField(null=True, blank=True)
    notes = models.TextField(blank=True)
    
    def __str__(self):
        return f"{self.student.username} - {self.reward.name}"

# apps/verification/models.py
from django.db import models
from apps.activities.models import Activity
import json

class GPSTrackingData(models.Model):
    activity = models.ForeignKey(Activity, on_delete=models.CASCADE, related_name='gps_tracking')
    tracking_data = models.JSONField()  # Store GPS points as JSON
    total_distance = models.DecimalField(max_digits=10, decimal_places=2)
    average_speed = models.DecimalField(max_digits=8, decimal_places=2)
    max_speed = models.DecimalField(max_digits=8, decimal_places=2)
    duration_seconds = models.IntegerField()
    verification_score = models.DecimalField(max_digits=5, decimal_places=2, null=True)
    is_verified = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"GPS Data for {self.activity}"

class VerificationLog(models.Model):
    activity = models.ForeignKey(Activity, on_delete=models.CASCADE, related_name='verification_logs')
    verification_type = models.CharField(max_length=50)
    result = models.CharField(max_length=20, choices=[
        ('passed', 'Passed'),
        ('failed', 'Failed'),
        ('warning', 'Warning'),
    ])
    details = models.JSONField()
    score = models.DecimalField(max_digits=5, decimal_places=2, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"{self.verification_type} - {self.result} for {self.activity}"
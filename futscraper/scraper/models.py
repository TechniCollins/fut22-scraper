from django.db import models

from django.contrib.auth import get_user_model

User = get_user_model()

class BusinessDetail(models.Model):
	user = models.ForeignKey(User, on_delete=models.CASCADE)
	business_name = models.CharField(max_length=200)
	ea_email = models.EmailField(max_length=240)  # The email used to sign in to the FUT web app
	ea_password = models.CharField(max_length=100)  # Store this more securely in future
	chrome_profile = models.CharField(max_length=200, blank=True)  # Path to the temp file for a user's Chrome profile

	def __str__(self):
		return self.business_name


# Table for storing verification codes
class VerificationCode(models.Model):
	user = models.ForeignKey(User, on_delete=models.CASCADE)
	code = models.CharField(max_length=40)


# Table for storing number of matches against time
class MatchCount(models.Model):
	user = models.ForeignKey(User, on_delete=models.CASCADE)
	time = models.DateTimeField(auto_now_add=True)
	count = models.IntegerField()

	def __str__(self):
		return f"{self.time}"

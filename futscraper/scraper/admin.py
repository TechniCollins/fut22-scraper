from django.contrib import admin
from scraper.models import BusinessDetail, VerificationCode, MatchCount

@admin.register(BusinessDetail)
class BusinessDetailAdmin(admin.ModelAdmin):
    readonly_fields = ['chrome_profile']

@admin.register(VerificationCode)
class VerificationCodeAdmin(admin.ModelAdmin):
    pass

@admin.register(MatchCount)
class MatchCountAdmin(admin.ModelAdmin):
    readonly_fields = ['count', 'user', 'time']

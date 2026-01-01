# Generated migration to create default credit packages

from django.db import migrations


def create_credit_packages(apps, schema_editor):
    CreditPackage = apps.get_model('core', 'CreditPackage')
    
    packages = [
        {'name': 'Starter Pack', 'credits': 5, 'price_cents': 100},
        {'name': 'Value Pack', 'credits': 25, 'price_cents': 400},
        {'name': 'Pro Pack', 'credits': 100, 'price_cents': 1500},
    ]
    
    for pkg in packages:
        CreditPackage.objects.get_or_create(
            credits=pkg['credits'],
            defaults={
                'name': pkg['name'],
                'price_cents': pkg['price_cents'],
                'is_active': True,
            }
        )


def remove_credit_packages(apps, schema_editor):
    CreditPackage = apps.get_model('core', 'CreditPackage')
    CreditPackage.objects.filter(credits__in=[5, 25, 100]).delete()


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0002_job_output_format'),
    ]

    operations = [
        migrations.RunPython(create_credit_packages, remove_credit_packages),
    ]

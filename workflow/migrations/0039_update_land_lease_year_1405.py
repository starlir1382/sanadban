from django.db import migrations


def update_lease_year_to_1405(apps, schema_editor):
    HousingDossier = apps.get_model("workflow", "HousingDossier")
    # Update existing dossiers that have old 1403 or empty year to current official base year 1405
    HousingDossier.objects.filter(land_lease_year__in=["1403", ""]).update(land_lease_year="1405")


def reverse_func(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ("workflow", "0038_housingdossier_cash_rent_confirmed_at_and_more"),
    ]

    operations = [
        migrations.RunPython(update_lease_year_to_1405, reverse_func),
    ]

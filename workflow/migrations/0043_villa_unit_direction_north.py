from django.db import migrations
from django.db.models import Q


def set_villa_unit_direction_north(apps, schema_editor):
    HousingDossier = apps.get_model("workflow", "HousingDossier")
    HousingDossier.objects.filter(
        Q(construction_type__icontains="ویلایی")
        | Q(site__icontains="جعفریه")
        | Q(site__icontains="سلفچگان")
        | Q(site__icontains="قنوات")
        | Q(site__icontains="پرنیان")
    ).exclude(unit_direction="شمالی").update(unit_direction="شمالی")

    PreSelectedUnit = apps.get_model("workflow", "PreSelectedUnit")
    PreSelectedUnit.objects.filter(
        Q(construction_type__icontains="ویلایی")
        | Q(site__name__icontains="جعفریه")
        | Q(site__name__icontains="سلفچگان")
        | Q(site__name__icontains="قنوات")
        | Q(site__name__icontains="پرنیان")
    ).exclude(unit_direction="شمالی").update(unit_direction="شمالی")


class Migration(migrations.Migration):

    dependencies = [
        ("workflow", "0042_lease_contract_section"),
    ]

    operations = [
        migrations.RunPython(set_villa_unit_direction_north, migrations.RunPython.noop),
    ]

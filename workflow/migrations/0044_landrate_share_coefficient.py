from decimal import Decimal
from django.db import migrations, models
from django.db.models import F


def combine_share_coefficients(apps, schema_editor):
    LandRate = apps.get_model("workflow", "LandRate")
    LandRate.objects.update(share_coefficient=F("share_land") + F("share_common"))


def split_share_coefficients(apps, schema_editor):
    LandRate = apps.get_model("workflow", "LandRate")
    LandRate.objects.update(share_land=F("share_coefficient"), share_common=Decimal("0"))


class Migration(migrations.Migration):

    dependencies = [
        ("workflow", "0043_villa_unit_direction_north"),
    ]

    operations = [
        migrations.AddField(
            model_name="landrate",
            name="share_coefficient",
            field=models.DecimalField(
                decimal_places=9,
                default=0,
                max_digits=14,
                verbose_name="مجموع ضریب قدرالسهم",
            ),
        ),
        migrations.RunPython(combine_share_coefficients, split_share_coefficients),
        migrations.RemoveField(
            model_name="landrate",
            name="share_common",
        ),
        migrations.RemoveField(
            model_name="landrate",
            name="share_land",
        ),
    ]

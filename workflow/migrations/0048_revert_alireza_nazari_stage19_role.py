from django.db import migrations


NEW_ALIREZA_ROLE_TITLE = "مدیر سامانه / مسئول مراحل ۱۷ و ۱۸"
OLD_STAGE19_ROLE_FRAGMENTS = ("کارشناس تسویه با پیمانکار", "تسویه با پیمانکار")


def revert_stage19_from_alireza_nazari(apps, schema_editor):
    UserProfile = apps.get_model("workflow", "UserProfile")
    WorkflowSignatureLog = apps.get_model("workflow", "WorkflowSignatureLog")

    for profile in UserProfile.objects.filter(
        user__username__in=["alireza_nazari", "alireza-nazari"]
    ):
        title = (profile.role_title or "").strip()
        if any(frag in title for frag in OLD_STAGE19_ROLE_FRAGMENTS):
            profile.role_title = NEW_ALIREZA_ROLE_TITLE
            profile.save(update_fields=["role_title"])

    for log in WorkflowSignatureLog.objects.filter(actor__icontains="نظری"):
        role = (log.role or "").strip()
        if any(frag in role for frag in OLD_STAGE19_ROLE_FRAGMENTS):
            log.role = NEW_ALIREZA_ROLE_TITLE
            log.save(update_fields=["role"])


def noop_reverse(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ("workflow", "0047_split_directorate_shipments_loan_prep"),
    ]

    operations = [
        migrations.RunPython(revert_stage19_from_alireza_nazari, noop_reverse),
    ]

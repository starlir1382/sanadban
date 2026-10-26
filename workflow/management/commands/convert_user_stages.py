import sys
from django.core.management.base import BaseCommand
from workflow.stages import convert_allowed_stages_string
from workflow.models import UserProfile


class Command(BaseCommand):
    help = "Converts UserProfile.allowed_stages to official 21-step workflow and applies overrides."

    def handle(self, *args, **options):
        sys.stdout.reconfigure(encoding="utf-8")

        overrides = {
            "decile_check_expert": "16",
            "revenue_expert": "17",
            "notary_letter_expert": "19,20",
        }

        profiles = list(UserProfile.objects.select_related("user").all().order_by("user__id"))
        table_rows = []

        for p in profiles:
            u = p.user
            old_val = p.allowed_stages
            if u.username in overrides:
                new_val = overrides[u.username]
            else:
                new_val = convert_allowed_stages_string(old_val, forward=True)
            p.allowed_stages = new_val
            p.save(update_fields=["allowed_stages"])
            table_rows.append((u.id, u.username, p.role_title or "", old_val, new_val))

        header = "| {:<3} | {:<25} | {:<35} | {:<20} | {:<20} |".format(
            "ID", "Username", "Role", "Old Allowed", "New Allowed"
        )
        sep = "|-----|---------------------------|-------------------------------------|----------------------|----------------------|"
        self.stdout.write(header)
        self.stdout.write(sep)
        for r in table_rows:
            self.stdout.write(
                "| {:<3} | {:<25} | {:<35} | {:<20} | {:<20} |".format(
                    r[0], r[1], r[2], r[3], r[4]
                )
            )

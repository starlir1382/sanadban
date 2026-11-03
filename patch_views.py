import os
import re
import shutil
import time
import py_compile

HERE = os.path.dirname(os.path.abspath(__file__))
PATH = os.path.join(HERE, "workflow", "views.py")

NEW_SIGN = '''@login_required(login_url='login')
@require_POST
@transaction.atomic
def electronic_sign_action(request, pk):
    """Interactive electronic signature. Uses the same logic as Excel group signing."""
    dossier = get_object_or_404(
        HousingDossier.objects.select_for_update(), archive_number=pk
    )

    if dossier.is_locked:
        return JsonResponse(
            {"status": "error", "message": "این پرونده نهایی و مختومه گردیده است."},
            status=400,
        )

    try:
        body_data = json.loads(request.body.decode("utf-8")) if request.body else {}
    except Exception:
        body_data = {}
    notes = (
        body_data.get("notes")
        or request.POST.get("notes")
        or "تایید و امضای الکترونیکی با موفقیت انجام شد."
    )

    ok, result = execute_dossier_sign(dossier, request.user, notes=notes)
    if not ok:
        return JsonResponse({"status": "error", "message": result}, status=403)

    profile = getattr(request.user, "profile", None)
    is_full_admin = (
        request.user.is_superuser
        or request.user.is_staff
        or bool(profile and (profile.is_housing_chief or profile.allowed_stages == "all"))
    )
    can_access_next = is_full_admin or bool(profile and profile.can_action_stage(dossier.current_stage))

    if can_access_next:
        redirect_url = reverse("dossier_detail", kwargs={"pk": dossier.archive_number})
    else:
        redirect_url = reverse("dossier_list")
        if dossier.is_locked:
            messages.success(request, f"پرونده #{dossier.archive_number} تایید و به بایگانی نهایی منتقل گردید.")
        else:
            messages.success(
                request,
                f"پرونده #{dossier.archive_number} با موفقیت به مرحله {dossier.current_stage} ({dossier.current_stage_title}) ارسال گردید.",
            )

    if request.headers.get("HX-Request"):
        return redirect(redirect_url)

    last_log = dossier.audit_logs.order_by("-timestamp").first()
    return JsonResponse({
        "status": "success",
        "new_stage": dossier.current_stage,
        "is_locked": dossier.is_locked,
        "hash": last_log.signature_hash if last_log else "",
        "redirect_url": redirect_url,
        "message": f"پرونده با موفقیت به مرحله {dossier.current_stage} منتقل گردید.",
    })


'''

NEW_PARSE_DATE = '''def _parse_filter_date(raw):
    """Parse YYYY/MM/DD or YYYY-MM-DD (Jalali or Gregorian) into a Gregorian date, or None."""
    if not raw:
        return None
    import datetime
    import jdatetime
    s = normalize_digits(raw, "ascii").replace("-", "/").strip()
    try:
        y, m, d = [int(p) for p in s.split("/")]
    except ValueError:
        return None
    try:
        if y < 1700:
            return jdatetime.date(y, m, d).togregorian()
        return datetime.date(y, m, d)
    except ValueError:
        return None


'''


def main():
    if not os.path.exists(PATH):
        print("ERROR: not found:", PATH)
        return

    backup = PATH + ".bak_" + time.strftime("%Y%m%d_%H%M%S")
    shutil.copy2(PATH, backup)
    print("Backup saved:", backup)

    with open(PATH, "rb") as f:
        text = f.read().decode("utf-8")
    nl = "\r\n" if "\r\n" in text else "\n"
    text = text.replace("\r\n", "\n")

    # 1) imports
    if re.search(r"^from django\.http import .*FileResponse", text, re.M):
        print("[1] imports: already patched, skipped")
    else:
        pat = r"^from django\.http import JsonResponse, HttpResponseBadRequest, HttpResponse[ \t]*$"
        new_imp = (
            "from django.http import JsonResponse, HttpResponseBadRequest, HttpResponse, FileResponse, Http404\n"
            "from django.urls import reverse"
        )
        text, n = re.subn(pat, new_imp, text, count=1, flags=re.M)
        print("[1] imports:", "patched" if n else "NOT FOUND (edit manually)")

    # 2) electronic_sign_action
    m = re.search(r"^def electronic_sign_action\(request, pk\):", text, re.M)
    if not m:
        print("[2] electronic_sign_action: NOT FOUND")
    else:
        nxt = re.search(r"^(?:@|def |class )", text[m.end():], re.M)
        end = m.end() + nxt.start() if nxt else len(text)
        segment = text[m.start():end]
        if "execute_dossier_sign(dossier, request.user" in segment:
            print("[2] electronic_sign_action: already patched, skipped")
        else:
            start = m.start()
            dm = re.search(r"(?:^@[^\n]*\n\s*)+\Z", text[:start], re.M)
            if dm:
                start = dm.start()
            text = text[:start] + NEW_SIGN + text[end:]
            print("[2] electronic_sign_action: replaced")

    # 3) stage cap 21 -> 22
    if "if 1 <= stg <= 21:" in text:
        text = text.replace("if 1 <= stg <= 21:", "if 1 <= stg <= 22:")
        print("[3] stage cap: patched")
    else:
        print("[3] stage cap: not found / already patched")

    # 4) broken Content-Disposition header
    bad = """resp["Content-Disposition"] = f'attachment; filename="{enc_fname}"; filename*=UTF-8''{enc_fname}'"""
    good = """resp["Content-Disposition"] = f"attachment; filename=\\"{enc_fname}\\"; filename*=UTF-8''{enc_fname}\""""
    if bad in text:
        text = text.replace(bad, good)
        print("[4] Content-Disposition: patched")
    else:
        print("[4] Content-Disposition: not found / already patched")

    # 5) _parse_filter_date
    if "def _parse_filter_date" in text:
        print("[5] _parse_filter_date: already exists, skipped")
    else:
        m5 = re.search(r"^def excel_export_all_view", text, re.M)
        if m5:
            text = text[:m5.start()] + NEW_PARSE_DATE + text[m5.start():]
            print("[5] _parse_filter_date: added")
        else:
            print("[5] excel_export_all_view NOT FOUND")

    with open(PATH, "wb") as f:
        f.write(text.replace("\n", nl).encode("utf-8"))

    try:
        py_compile.compile(PATH, doraise=True)
        print("\nOK: views.py compiles. Now run migrate and restart Waitress.")
    except py_compile.PyCompileError as e:
        shutil.copy2(backup, PATH)
        print("\nCOMPILE ERROR, original restored from backup:\n", e)


if __name__ == "__main__":
    main()
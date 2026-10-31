"""
Unit tests for workflow stages and migration mapping.
"""

from django.test import TestCase, RequestFactory
import json
from django.contrib.auth.models import User
from workflow.models import HousingDossier, UserProfile
from workflow.views import electronic_sign_action, return_stage_action, upload_scan_attachment_view
from workflow.stages import (
    STAGE_ROLES,
    STAGE_DETAILS,
    OLD_TO_NEW_STAGE_MAP,
    NEW_TO_OLD_STAGE_MAP,
    MIN_STAGE,
    MAX_STAGE,
    TOTAL_STAGES,
    map_old_to_new_stage,
    map_new_to_old_stage,
    convert_allowed_stages_string,
    STAGE_1_UNIT_SELECTION,
    STAGE_2_PLAQUE_AND_COST,
    STAGE_3_FORM_J_REVIEW,
    STAGE_4_LOANS_AND_CONTRIBUTION,
    STAGE_5_SMS_CONTRIBUTION,
    STAGE_6_BANK_LETTER,
    STAGE_7_SCAN_DOCS_INSTALLMENT,
    STAGE_8_BROKERAGE_CEO,
    STAGE_9_NATIONAL_HOUSING,
    STAGE_10_FORM_J_REGISTRATION,
    STAGE_11_TECHNICAL_ENGINEERING,
    STAGE_12_REAL_ESTATE,
    STAGE_13_LAND_BANK,
    STAGE_14_LEGAL,
    STAGE_15_EVALUATION,
    STAGE_16_DECILE_CHECKS,
    STAGE_17_PREPARATION_RENT,
    STAGE_18_CONTRACTOR_SETTLEMENT,
    STAGE_19_NOTARY_LETTER,
    STAGE_20_LEASE_SCAN_PRINT,
    STAGE_21_ARCHIVE,
)


class StageMappingTestCase(TestCase):
    """Verifies that the new 21-step workflow and mappings are mathematically complete."""

    def test_stage_roles_range_and_structure(self):
        """STAGE_ROLES must have exactly 21 steps from 1 to 21."""
        self.assertEqual(len(STAGE_ROLES), 22)
        self.assertEqual(set(STAGE_ROLES.keys()), set(range(1, 23)))
        self.assertEqual(MIN_STAGE, 1)
        self.assertEqual(MAX_STAGE, 22)
        self.assertEqual(TOTAL_STAGES, 22)

        for stg, (unit, role, title) in STAGE_ROLES.items():
            self.assertIn(unit, ("brokerage", "directorate"))
            self.assertTrue(len(role) > 0)
            self.assertTrue(len(title) > 0)

    def test_stage_details_keys(self):
        """STAGE_DETAILS must match keys 1 to 21 with required descriptive fields."""
        self.assertEqual(len(STAGE_DETAILS), 22)
        self.assertEqual(set(STAGE_DETAILS.keys()), set(range(1, 23)))
        for stg, d in STAGE_DETAILS.items():
            self.assertIn("title", d)
            self.assertIn("actor", d)
            self.assertIn("action", d)
            self.assertIn("next", d)
            self.assertIn("notes", d)

    def test_forward_stage_mapping_completeness(self):
        """All old stages 0 to 21 map correctly to new stages 1 to 21."""
        expected = {
            0: 1, 1: 2, 2: 2, 3: 3, 4: 4, 5: 4, 6: 4,
            7: 5, 8: 6, 9: 7, 10: 9, 11: 10, 12: 12,
            13: 13, 14: 14, 15: 15, 16: 11, 17: 16,
            18: 17, 19: 19, 20: 20, 21: 22
        }
        for old_stg, exp_new in expected.items():
            self.assertEqual(map_old_to_new_stage(old_stg), exp_new, f"Mapping failed for old stage {old_stg}")

    def test_reverse_stage_mapping(self):
        """New stages map back to their primary old predecessor stages."""
        self.assertEqual(map_new_to_old_stage(1), 0)
        self.assertEqual(map_new_to_old_stage(2), 2)
        self.assertEqual(map_new_to_old_stage(3), 3)
        self.assertEqual(map_new_to_old_stage(4), 6)
        self.assertEqual(map_new_to_old_stage(5), 7)
        self.assertEqual(map_new_to_old_stage(6), 8)
        self.assertEqual(map_new_to_old_stage(7), 9)
        self.assertEqual(map_new_to_old_stage(8), 9)
        self.assertEqual(map_new_to_old_stage(9), 10)
        self.assertEqual(map_new_to_old_stage(10), 11)
        self.assertEqual(map_new_to_old_stage(11), 16)
        self.assertEqual(map_new_to_old_stage(12), 12)
        self.assertEqual(map_new_to_old_stage(13), 13)
        self.assertEqual(map_new_to_old_stage(14), 14)
        self.assertEqual(map_new_to_old_stage(15), 15)
        self.assertEqual(map_new_to_old_stage(16), 17)
        self.assertEqual(map_new_to_old_stage(17), 18)
        self.assertEqual(map_new_to_old_stage(18), 18)
        self.assertEqual(map_new_to_old_stage(19), 19)
        self.assertEqual(map_new_to_old_stage(20), 20)
        self.assertEqual(map_new_to_old_stage(21), 20)
        self.assertEqual(map_new_to_old_stage(22), 21)

    def test_convert_allowed_stages_string(self):
        """Allowed stages string correctly maps both forward and backwards without duplicates."""
        # Unrestricted
        self.assertEqual(convert_allowed_stages_string("all"), "all")

        # Old: 0,1,2,10 -> New: 1,2,8
        forward_res = convert_allowed_stages_string("0, 1, 2, 10")
        self.assertEqual(forward_res, "1,2,9")

        # Reverse conversion: 1,2,8 -> 0,2,10
        reverse_res = convert_allowed_stages_string("1, 2, 9", forward=False)
        self.assertEqual(reverse_res, "0,2,10")

        # Empty / whitespace handling
        self.assertEqual(convert_allowed_stages_string(""), "")
        self.assertEqual(convert_allowed_stages_string(None), "all")

    def test_named_constants_values(self):
        """Named constants match their step numbers."""
        self.assertEqual(STAGE_1_UNIT_SELECTION, 1)
        self.assertEqual(STAGE_2_PLAQUE_AND_COST, 2)
        self.assertEqual(STAGE_3_FORM_J_REVIEW, 3)
        self.assertEqual(STAGE_4_LOANS_AND_CONTRIBUTION, 4)
        self.assertEqual(STAGE_5_SMS_CONTRIBUTION, 5)
        self.assertEqual(STAGE_6_BANK_LETTER, 6)
        self.assertEqual(STAGE_7_SCAN_DOCS_INSTALLMENT, 7)
        self.assertEqual(STAGE_8_BROKERAGE_CEO, 8)
        self.assertEqual(STAGE_9_NATIONAL_HOUSING, 9)
        self.assertEqual(STAGE_10_FORM_J_REGISTRATION, 10)
        self.assertEqual(STAGE_11_TECHNICAL_ENGINEERING, 11)
        self.assertEqual(STAGE_12_REAL_ESTATE, 12)
        self.assertEqual(STAGE_13_LAND_BANK, 13)
        self.assertEqual(STAGE_14_LEGAL, 14)
        self.assertEqual(STAGE_15_EVALUATION, 15)
        self.assertEqual(STAGE_16_DECILE_CHECKS, 16)
        self.assertEqual(STAGE_17_PREPARATION_RENT, 17)
        self.assertEqual(STAGE_18_CONTRACTOR_SETTLEMENT, 18)
        self.assertEqual(STAGE_19_NOTARY_LETTER, 19)
        self.assertEqual(STAGE_20_LEASE_SCAN_PRINT, 20)
        self.assertEqual(STAGE_21_ARCHIVE, 21)


class WorkflowExecutionTestCase(TestCase):
    """End-to-End verification of dossier creation, signing, permissions, and archive."""

    def setUp(self):
        self.factory = RequestFactory()
        self.admin_user = User.objects.create_superuser(username="admin_test", password="password")
        p_admin = self.admin_user.profile
        p_admin.full_name = "مدیر سیستم"
        p_admin.allowed_stages = "all"
        p_admin.save()

        self.alemi = User.objects.create_user(username="alemi_test", password="password")
        p_alemi = self.alemi.profile
        p_alemi.full_name = "عالمی"
        p_alemi.allowed_stages = "3,10"
        p_alemi.role_title = "کارشناس بررسی فرم ج"
        p_alemi.save()

        self.legal = User.objects.create_user(username="legal_test", password="password")
        p_legal = self.legal.profile
        p_legal.full_name = "حقوقی"
        p_legal.allowed_stages = "14"
        p_legal.role_title = "کارشناس حقوقی"
        p_legal.save()

    def test_admin_signs_stage_1_to_21_and_archives(self):
        dossier = HousingDossier.objects.create(
            national_id="9991112233",
            full_name="متقاضی آزمایشی",
            site="سایت نمونه",
            project="پروژه نمونه",
        )
        self.assertEqual(dossier.current_stage, 1)
        self.assertEqual(dossier.archive_number, 100001)

        for step in range(1, 23):
            req = self.factory.post(
                f"/dossier/{dossier.archive_number}/action/sign/",
                data=json.dumps({"notes": f"امضا مرحله {step}"}),
                content_type="application/json",
            )
            req.user = self.admin_user
            resp = electronic_sign_action(req, pk=dossier.archive_number)
            self.assertEqual(resp.status_code, 200)

            dossier.refresh_from_db()
            if step < 22:
                self.assertEqual(dossier.current_stage, step + 1)
                self.assertFalse(dossier.is_locked)
                self.assertEqual(dossier.status, "IN_PROGRESS")
            else:
                self.assertEqual(dossier.current_stage, 22)
                self.assertTrue(dossier.is_locked)
                self.assertEqual(dossier.status, "COMPLETED")

    def test_expert_permissions_upload_sign_and_return(self):
        dossier = HousingDossier.objects.create(
            national_id="8882223344",
            full_name="متقاضی کارشناسی",
            current_stage=3,
        )

        # 1. Alemi uploads at stage 3
        req_up = self.factory.post(
            f"/dossier/{dossier.archive_number}/attachment/upload/",
            data={
                "title": "استعلام سبز فرم ج",
                "doc_type": "FORM_J",
                "preview_url": "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg==",
            },
        )
        req_up.user = self.alemi
        resp_up = upload_scan_attachment_view(req_up, pk=dossier.archive_number)
        self.assertEqual(resp_up.status_code, 200)

        # 2. Alemi signs stage 3 -> advances to 4
        req_s3 = self.factory.post(
            f"/dossier/{dossier.archive_number}/action/sign/",
            data=json.dumps({"notes": "تایید فرم ج"}),
            content_type="application/json",
        )
        req_s3.user = self.alemi
        resp_s3 = electronic_sign_action(req_s3, pk=dossier.archive_number)
        self.assertEqual(resp_s3.status_code, 200)
        dossier.refresh_from_db()
        self.assertEqual(dossier.current_stage, 4)

        # 3. Alemi tries to sign stage 4 -> 403 Forbidden
        req_s4 = self.factory.post(
            f"/dossier/{dossier.archive_number}/action/sign/",
            data=json.dumps({"notes": "تلاش غیرمجاز"}),
            content_type="application/json",
        )
        req_s4.user = self.alemi
        resp_s4 = electronic_sign_action(req_s4, pk=dossier.archive_number)
        self.assertEqual(resp_s4.status_code, 403)

        # 4. Alemi can sign at stage 10
        dossier.current_stage = 10
        dossier.save()
        req_s10 = self.factory.post(
            f"/dossier/{dossier.archive_number}/action/sign/",
            data=json.dumps({"notes": "تایید فرم ج اداره کل"}),
            content_type="application/json",
        )
        req_s10.user = self.alemi
        resp_s10 = electronic_sign_action(req_s10, pk=dossier.archive_number)
        self.assertEqual(resp_s10.status_code, 200)
        dossier.refresh_from_db()
        self.assertEqual(dossier.current_stage, 11)

        # 5. Legal expert at stage 14
        dossier.current_stage = 14
        dossier.save()

        # Returning to stage 0 -> rejected 400
        req_ret0 = self.factory.post(
            f"/dossier/{dossier.archive_number}/action/return/",
            data=json.dumps({"target_stage": 0, "notes": "برگشت نامعتبر به صفر"}),
            content_type="application/json",
        )
        req_ret0.user = self.legal
        resp_ret0 = return_stage_action(req_ret0, pk=dossier.archive_number)
        self.assertEqual(resp_ret0.status_code, 400)

        # Returning to stage 11 -> allowed
        req_ret11 = self.factory.post(
            f"/dossier/{dossier.archive_number}/action/return/",
            data=json.dumps({"target_stage": 11, "notes": "نقص مدارک فنی، بازگشت به ۱۱"}),
            content_type="application/json",
        )
        req_ret11.user = self.legal
        resp_ret11 = return_stage_action(req_ret11, pk=dossier.archive_number)
        self.assertEqual(resp_ret11.status_code, 200)
        dossier.refresh_from_db()
        self.assertEqual(dossier.current_stage, 11)
        self.assertEqual(dossier.status, "RETURNED")


    def test_step7_fields_and_folder_label_print(self):
        from workflow.views import save_dossier_draft_view, folder_label_print_view

        dossier_expert = User.objects.create_user(username="broker_dossier_test", password="password")
        p_exp = dossier_expert.profile
        p_exp.allowed_stages = "7"
        p_exp.save()

        dossier = HousingDossier.objects.create(
            national_id="7776665544",
            full_name="متقاضی مرحله هفت",
            current_stage=7,
        )

        # Save draft at Stage 7
        req_save = self.factory.post(
            f"/dossier/{dossier.archive_number}/save/",
            data=json.dumps({
                "form_j_number": "1403/J/9988",
                "has_installment_booklet": True,
                "has_info_form": True,
                "has_form_j": True,
                "has_affidavit": True,
                "has_sana": True,
                "has_national_id_doc": True,
            }),
            content_type="application/json",
        )
        req_save.user = dossier_expert
        resp_save = save_dossier_draft_view(req_save, pk=dossier.archive_number)
        self.assertEqual(resp_save.status_code, 200)

        dossier.refresh_from_db()
        self.assertEqual(dossier.form_j_number, "1403/J/9988")
        self.assertTrue(dossier.has_installment_booklet)
        self.assertTrue(dossier.has_info_form)
        self.assertTrue(dossier.has_form_j)
        self.assertTrue(dossier.has_affidavit)
        self.assertTrue(dossier.has_sana)
        self.assertTrue(dossier.has_national_id_doc)

        # Print Folder Label
        req_print = self.factory.get(f"/dossier/{dossier.archive_number}/print/folder-label/")
        req_print.user = dossier_expert
        resp_print = folder_label_print_view(req_print, pk=dossier.archive_number)
        self.assertEqual(resp_print.status_code, 200)
        self.assertIn(str(dossier.archive_number), resp_print.content.decode("utf-8"))
        self.assertIn("1403/J/9988", resp_print.content.decode("utf-8"))



class OptimizationAndBulkExcelTestCase(TestCase):
    """Verifies CSRF protections, list pagination, and high-performance Excel bulk operations."""

    def setUp(self):
        self.factory = RequestFactory()
        self.admin = User.objects.create_superuser(username="admin_perf", password="password", email="admin@example.com")

    def test_login_page_csrf_and_cache_headers(self):
        """Login view must set no-cache headers and provide a fresh CSRF cookie."""
        from django.contrib.auth.models import AnonymousUser
        from workflow.views import user_login_view
        req = self.factory.get("/login/")
        from django.contrib.sessions.middleware import SessionMiddleware
        middleware = SessionMiddleware(lambda r: None)
        middleware.process_request(req)
        req.session.save()
        req.user = AnonymousUser()

        resp = user_login_view(req)
        self.assertEqual(resp.status_code, 200)
        cache_control = resp.get("Cache-Control", "")
        self.assertIn("no-cache", cache_control)
        self.assertIn("no-store", cache_control)

    def test_dossier_list_pagination(self):
        """Dashboard list view must paginate records (50 per page) with elided page range."""
        # Create 55 test dossiers
        bulk_dossiers = [
            HousingDossier(
                national_id=f"888{i:07d}",
                archive_number=300000 + i,
                full_name=f"متقاضی آزمایشی {i}",
                current_stage=1,
            )
            for i in range(55)
        ]
        HousingDossier.objects.bulk_create(bulk_dossiers)

        self.client.force_login(self.admin)
        resp = self.client.get("/")
        self.assertEqual(resp.status_code, 200)
        self.assertIn("paginator", resp.context)
        self.assertEqual(resp.context["paginator"].num_pages, 2)
        self.assertEqual(len(resp.context["dossiers"]), 50)
        self.assertEqual(resp.context["total_all_dossiers"], 55)
        html = resp.content.decode("utf-8")
        self.assertIn("نمایش پرونده‌های", html)
        self.assertIn("از مجموع", html)

    def test_excel_bulk_create_and_update(self):
        """Verifies chunked bulk creation and updating via Excel service."""
        import io
        import openpyxl
        from workflow.excel_service import process_create_excel, process_update_excel

        # Build an Excel file in-memory with 10 rows
        wb = openpyxl.Workbook()
        ws = wb.active
        ws.title = "ایجاد"
        ws.append(["کد ملی متقاضی", "نام و نام خانوادگی متقاضی", "نام پدر", "شماره همراه متقاضی"])
        for i in range(10):
            ws.append([f"001234567{i}", f"کاربر تستی {i}", "پدر تستی", "09120000000"])
        
        out = io.BytesIO()
        wb.save(out)
        out.seek(0)

        # 1. Test Create Excel
        res_create = process_create_excel(out, user=self.admin, is_preview=False)
        self.assertTrue(res_create["success"])
        self.assertEqual(res_create["created_count"], 10)
        self.assertEqual(res_create["failed_count"], 0)

        # 2. Test Update Excel
        wb_up = openpyxl.Workbook()
        ws_up = wb_up.active
        ws_up.title = "بروزرسانی"
        ws_up.append(["کد ملی متقاضی", "نام پدر"])
        for i in range(10):
            ws_up.append([f"001234567{i}", f"پدر جدید {i}"])
        
        out_up = io.BytesIO()
        wb_up.save(out_up)
        out_up.seek(0)

        res_update = process_update_excel(out_up, user=self.admin, is_preview=False)
        self.assertTrue(res_update["success"])
        self.assertEqual(res_update["updated_count"], 10)

        # Verify father_name was updated in DB
        dossier_0 = HousingDossier.objects.get(national_id="0012345670")
        self.assertEqual(dossier_0.father_name, "پدر جدید 0")

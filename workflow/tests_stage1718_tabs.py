from django.test import TestCase, Client
from django.contrib.auth.models import User
from workflow.models import HousingDossier, UserProfile
import json

class Stage1718TabsTestCase(TestCase):
    def setUp(self):
        # Create stage 17/18 user
        self.user_1718 = User.objects.create_user(username='test_ztk', password='password123')
        self.profile_1718 = getattr(self.user_1718, 'profile', None) or UserProfile.objects.get_or_create(user=self.user_1718)[0]
        self.profile_1718.allowed_stages = '17,18'
        self.profile_1718.organization = 'consultant'
        self.profile_1718.save()
        
        # Create regular user (stage 1)
        self.user_stg1 = User.objects.create_user(username='test_stg1', password='password123')
        self.profile_stg1 = getattr(self.user_stg1, 'profile', None) or UserProfile.objects.get_or_create(user=self.user_stg1)[0]
        self.profile_stg1.allowed_stages = '1'
        self.profile_stg1.organization = 'consultant'
        self.profile_stg1.save()

        # Create dossiers in stage 17, 18, and stage 1
        self.d_s17 = HousingDossier.objects.create(
            current_stage=17,
            archive_number='170001',
            national_id='1111111111',
            full_name='متقاضی مرحله ۱۷'
        )
        self.d_s18 = HousingDossier.objects.create(
            current_stage=18,
            archive_number='180001',
            national_id='2222222222',
            full_name='متقاضی مرحله ۱۸'
        )
        self.d_s1 = HousingDossier.objects.create(
            current_stage=1,
            archive_number='100001',
            national_id='3333333333',
            full_name='متقاضی مرحله ۱'
        )

        self.client = Client()

    def test_default_home_page_shows_only_stage1718(self):
        self.client.force_login(self.user_1718)
        resp = self.client.get('/')
        self.assertEqual(resp.status_code, 200)
        self.assertTrue(resp.context['is_stage17_18_user'])
        self.assertEqual(resp.context['active_tab_1718'], 'stage1718')
        self.assertEqual(resp.context['count_stage1718'], 2)
        self.assertEqual(resp.context['count_other'], 1)
        self.assertEqual(resp.context['count_all'], 3)
        self.assertEqual(resp.context['dossiers_count'], 2)
        
        dossier_ids = [d.id for d in resp.context['dossiers']]
        self.assertIn(self.d_s17.id, dossier_ids)
        self.assertIn(self.d_s18.id, dossier_ids)
        self.assertNotIn(self.d_s1.id, dossier_ids)

    def test_other_tab_shows_non_stage1718(self):
        self.client.force_login(self.user_1718)
        resp = self.client.get('/?tab=other')
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.context['active_tab_1718'], 'other')
        self.assertEqual(resp.context['dossiers_count'], 1)
        
        dossier_ids = [d.id for d in resp.context['dossiers']]
        self.assertIn(self.d_s1.id, dossier_ids)
        self.assertNotIn(self.d_s17.id, dossier_ids)
        self.assertNotIn(self.d_s18.id, dossier_ids)

    def test_all_tab_shows_all_dossiers(self):
        self.client.force_login(self.user_1718)
        resp = self.client.get('/?tab=all')
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.context['active_tab_1718'], 'all')
        self.assertEqual(resp.context['dossiers_count'], 3)

    def test_search_searches_all_three_categories_from_stage1718_tab(self):
        self.client.force_login(self.user_1718)
        # Search for dossier at stage 1 while on tab stage1718
        resp = self.client.get('/?tab=stage1718&q=3333333333')
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.context['dossiers_count'], 1)
        dossier_ids = [d.id for d in resp.context['dossiers']]
        self.assertIn(self.d_s1.id, dossier_ids)

    def test_search_searches_all_three_categories_from_other_tab(self):
        self.client.force_login(self.user_1718)
        # Search for dossier at stage 17 while on tab other
        resp = self.client.get('/?tab=other&q=1111111111')
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.context['dossiers_count'], 1)
        dossier_ids = [d.id for d in resp.context['dossiers']]
        self.assertIn(self.d_s17.id, dossier_ids)

    def test_ajax_search_searches_across_all(self):
        self.client.force_login(self.user_1718)
        resp = self.client.get('/?tab=stage1718&q=100001&ajax=1')
        self.assertEqual(resp.status_code, 200)
        data = json.loads(resp.content)
        self.assertEqual(data['status'], 'success')
        self.assertEqual(data['count'], 1)
        self.assertIn('متقاضی مرحله ۱', data['html'])

    def test_regular_user_not_affected(self):
        self.client.force_login(self.user_stg1)
        resp = self.client.get('/')
        self.assertEqual(resp.status_code, 200)
        self.assertFalse(resp.context['is_stage17_18_user'])

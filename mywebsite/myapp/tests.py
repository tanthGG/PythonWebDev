from django.contrib.auth.models import User
from django.test import Client, TestCase
from django.urls import reverse

from .models import Profile, Staff, StaffFeedback


class StaffFeedbackTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="tester", password="pass1234")
        Profile.objects.create(user=self.user)
        self.staff = Staff.objects.create(name="Guide A")

    def test_authenticated_user_can_submit_like(self):
        client = Client()
        client.login(username="tester", password="pass1234")
        client.get(reverse("home"))
        response = client.post(
            reverse("staff-feedback", args=[self.staff.id]),
            {"sentiment": StaffFeedback.Sentiment.LIKE, "next": reverse("home")},
            follow=True,
        )
        self.assertEqual(response.status_code, 200)
        self.staff.refresh_from_db()
        self.assertEqual(self.staff.likes_total(), 1)

    def test_comment_requires_text(self):
        client = Client()
        client.login(username="tester", password="pass1234")
        client.get(reverse("home"))
        response = client.post(
            reverse("staff-feedback", args=[self.staff.id]),
            {"comment": "", "next": reverse("home")},
            follow=True,
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(StaffFeedback.objects.count(), 0)


class StaffInsightsTests(TestCase):
    def setUp(self):
        self.staff_member = Staff.objects.create(name="Guide B")
        self.admin_user = User.objects.create_user(
            username="manager", password="pass1234", is_staff=True
        )
        Profile.objects.create(user=self.admin_user, usertype="admin")

        self.regular_user = User.objects.create_user(username="guest", password="pass1234")
        Profile.objects.create(user=self.regular_user)

        StaffFeedback.objects.create(
            staff=self.staff_member,
            user=self.admin_user,
            sentiment=StaffFeedback.Sentiment.LIKE,
            comment="Great guide!",
        )

    def test_requires_login(self):
        client = Client()
        response = client.get(reverse("staff-insights"))
        self.assertEqual(response.status_code, 302)

    def test_regular_user_forbidden(self):
        client = Client()
        client.login(username="guest", password="pass1234")
        response = client.get(reverse("staff-insights"))
        self.assertEqual(response.status_code, 403)

    def test_staff_can_view_insights(self):
        client = Client()
        client.login(username="manager", password="pass1234")
        response = client.get(reverse("staff-insights"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Guide feedback insights")

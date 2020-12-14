from django.contrib.auth import get_user_model
from django.contrib.flatpages.models import FlatPage
from django.contrib.sites.models import Site

from django.test import TestCase, Client
from django.urls import reverse

from posts.models import Post, Group, User


class StaticURLTests(TestCase):
    def setUp(self):
        self.guest_client = Client()
        site = Site.objects.get(pk=1)
        self.fp_about = FlatPage.objects.create(
            url="/about-author/",
            title="Об авторе",
            content="<b>content</b>",
        )
        self.fp_tech = FlatPage.objects.create(
            url="/about-spec/",
            title="Технологии",
            content="<b>content</b>",
        )
        self.fp_about.sites.add(site)
        self.fp_tech.sites.add(site)
        self.static_pages = ("/about-author/", "/about-spec/")

    def test_static_pages_response(self):
        for url in self.static_pages:
            with self.subTest():
                response = self.guest_client.get(url)
                self.assertEqual(response.status_code, 200, f"url: {url}")


class PostURLTests(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.group = Group.objects.create(
            title="Test group",
            slug="test",
            description="Тестовая группа"
        )

    def setUp(self):
        self.guest_client = Client()
        self.user1 = User.objects.create(username="tester")
        self.authorized_client = Client()
        self.authorized_client.force_login(self.user1)
        self.user2 = User.objects.create(username="tester2")
        self.authorized_client2 = Client()
        self.authorized_client2.force_login(self.user2)

        self.post = Post.objects.create(
            text="Тестовый текст",
            author=self.user1,
            pub_date="01.01.2020",
            group=PostURLTests.group,
        )

    def test_url_exists_at_desired_location(self):
        """Страница 'index','group_post', 'profile', 'post'
        доступны любому пользователю."""
        url_status_code = [
            reverse("index"),
            reverse("group", args=[self.group.slug]),
            reverse("profile", args=[self.user1]),
            reverse("post", args=[self.user1, self.post.id,]),
        ]
        for value in url_status_code:
            response = self.guest_client.get(value)
            with self.subTest(value="Ошибка" + value):
                self.assertEqual(response.status_code, 200)

    def test_post_edit_author(self):
        response = self.authorized_client.get(reverse("post_edit",
                                              args=(self.user1, self.post.id)))
        self.assertEqual(response.status_code, 200)

    def test_post_edit_authorized_non_author(self):
        response = self.authorized_client2.get(reverse("post_edit",
                                               args=(self.user1.username, self.post.id)))
        self.assertEqual(response.status_code, 302)

    def test_post_edit_guest(self):
        template = reverse(
            "post_edit",
            args=(self.user1, self.post.id)
        )
        redirect_url = reverse("login") + "?next=" + reverse(
            "post_edit",
            args=(self.user1, self.post.id)
        )
        response = self.guest_client.get(template)
        self.assertRedirects(response, redirect_url)
        self.assertEqual(response.status_code, (302))

    def test_new_post_redirect_guest_to_login(self):
        response = self.guest_client.get(reverse("new_post"))
        self.assertRedirects(
            response, reverse("login") + "?next=" + reverse("new_post"))

    def test_urls_uses_correct_template(self):
        """URL-адрес использует соответствующий шаблон."""
        templates_reverse_name = {
            reverse("index"): "index.html",
            reverse("new_post"): "new.html",
            reverse("group", kwargs={"slug": self.group.slug}): "group.html",
            reverse("post_edit",
                    args=(self.user1, self.post.id)): "new.html",
            reverse("profile", args=[self.user1]): "profile.html",
            reverse("follow_index"): "follow.html",
        }
        for reverse_name, template in templates_reverse_name.items():
            with self.subTest(reverse_name=reverse_name):
                response = self.authorized_client.get(reverse_name)
                self.assertTemplateUsed(response, template)

    def test_comment_unauthorized_user(self):
        response = self.guest_client.get(reverse("add_comment",
                                                 args=(self.user1,
                                                       self.post.id)))
        self.assertEqual(response.status_code, 302)

    def test_404(self):
        response = self.authorized_client.get("/fail/")
        self.assertEqual(response.status_code, 404)

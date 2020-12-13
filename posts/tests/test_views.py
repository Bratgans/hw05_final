import shutil
from django.conf import settings

from django import forms

from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.cache import cache

from django.test import Client, TestCase
from django.urls import reverse

from posts.models import Comment, Post, Group, User, Follow

INDEX_URL = reverse("index")
NEW_POST_URL = reverse("new_post")


class PostPagesTests(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.group = Group.objects.create(
            title="Test group",
            slug="test",
            description="Тестовая группа"
        )
        Group.objects.create(
            title="Test group2",
            slug="test2",
            description="Тестовая группа 2"
        )

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(settings.MEDIA_ROOT, ignore_errors=True)
        super().tearDownClass()

    def setUp(self):
        self.guest_client = Client()
        self.user = User.objects.create(username="tester")
        self.authorized_client = Client()
        self.authorized_client.force_login(self.user)
        self.user2 = User.objects.create(username="tester2")
        self.authorized_client2 = Client()
        self.authorized_client2.force_login(self.user2)

        small_gif = (
            b'\x47\x49\x46\x38\x39\x61\x02\x00'
            b'\x01\x00\x80\x00\x00\x00\x00\x00'
            b'\xFF\xFF\xFF\x21\xF9\x04\x00\x00'
            b'\x00\x00\x00\x2C\x00\x00\x00\x00'
            b'\x02\x00\x01\x00\x00\x02\x02\x0C'
            b'\x0A\x00\x3B'
        )
        img = SimpleUploadedFile(
            name="small.gif",
            content=small_gif,
            content_type="image/gif"
        )
        self.post = Post.objects.create(
            text="Тестовый текст",
            author=self.user,
            pub_date="01.01.2020",
            group=PostPagesTests.group,
            image=img,
        )

    def test_pages_uses_correct_template(self):
        """URL-адрес использует соответствующий шаблон."""
        group_url = reverse("group", args=[self.group.slug])
        templates_page_names = {
            "index.html": INDEX_URL,
            "new.html": NEW_POST_URL,
            "group.html": group_url
        }
        for template, reverse_name in templates_page_names.items():
            with self.subTest(template=template):
                response = self.authorized_client.get(reverse_name)
                self.assertTemplateUsed(response, template)

    def test_index_show_correct_context(self):
        """Шаблон index сформирован с правильным контекстом."""
        response = self.guest_client.get(INDEX_URL)
        post = response.context["page"][0]
        self.assertEqual(post, self.post)

    def test_group_page_show_correct_context(self):
        """Шаблон group сформирован с правильным контекстом."""
        group_url = reverse("group", args=[self.group.slug])
        response = self.authorized_client.get(group_url)
        post = response.context["page"][0]
        self.assertEqual(post, self.post)

    def test_new_show_correct_context(self):
        """Шаблон new сформирован с правильным контекстом."""
        response = self.authorized_client.get(NEW_POST_URL)
        form_fields = {
            "text": forms.fields.CharField,
            "group": forms.fields.ChoiceField,
            "image": forms.fields.ImageField,
        }

        for value, expected in form_fields.items():
            with self.subTest(value=value):
                form_field = response.context.get("form").fields.get(value)
                self.assertIsInstance(form_field, expected)

    def test_profile_show_correct_context(self):
        """Шаблон profile сформирован с правильным контекстом."""
        profile_url = reverse("profile", args=[self.user.username])
        response = self.authorized_client.get(profile_url)
        post = response.context["page"][0]
        author = response.context.get("author")
        self.assertEqual(post, self.post)
        self.assertEqual(author, self.user)

    def test_post_edit_show_correct_context(self):
        """Шаблон post_edit сформирован с правильным контекстом."""
        edit_url = reverse("post_edit",
                           args=[self.user.username, self.post.id])
        response = self.authorized_client.get(edit_url)
        form_fields = {
            "text": forms.fields.CharField,
            "group": forms.fields.ChoiceField,
            "image": forms.fields.ImageField,
        }

        for value, expected in form_fields.items():
            with self.subTest(value=value):
                form_field = response.context.get("form").fields.get(value)
                self.assertIsInstance(form_field, expected)

    def test_post_show_correct_context(self):
        """Шаблон post сформирован с правильным контекстом."""
        profile_url = reverse("profile", args=[self.user.username])
        response = self.guest_client.get(profile_url)
        post = response.context.get("page")[0]
        self.assertEqual(post, self.post)

    def test_images_on_page(self):
        group_response = self.authorized_client.get(
                reverse("group", kwargs={"slug": self.group.slug})
        )
        profile_response = self.authorized_client.get(
                reverse(
                    "profile",
                    kwargs={"username": self.user.username}
                )
        )
        index_response = self.authorized_client.get(
                reverse("index")
        )
        index_image_post = index_response.context.get("page")[0].image
        group_image_post = group_response.context.get("page")[0].image
        profile_image_post = profile_response.context.get("page")[0].image
        self.assertTrue(index_image_post)
        self.assertTrue(group_image_post)
        self.assertTrue(profile_image_post)

    def test_comments(self):
        comment_count = Comment.objects.count()
        form_data = {
            "author": self.user,
            "post": self.post,
            "text": "Comment test",
        }
        self.guest_client.post(
            reverse("add_comment", kwargs={
                "username": self.post.author.username,
                "post_id": self.post.id
            }), data=form_data, follow=True,)
        self.authorized_client.post(
            reverse("add_comment",
                    kwargs={
                        "username": self.post.author.username,
                        "post_id": self.post.id
                    }),
            data=form_data,
            follow=True,
        )
        post_comment = Comment.objects.first()
        self.assertEqual(Comment.objects.count(), comment_count + 1)
        self.assertEqual(post_comment.text, "Comment test")
        self.assertEqual(post_comment.author, self.user)
        self.assertEqual(post_comment.post, self.post)

    def test_follow_index(self):
        """Новая запись пользователя появляется в ленте подписчика"""
        self.authorized_client2.get(
            reverse("profile_follow",
                    kwargs={"username": self.user}))
        response = self.authorized_client2.get(reverse("follow_index"))
        follow_post = response.context.get("page")[0]
        self.assertEqual(follow_post, self.post)

    def test_nonfollow_index(self):
        response2 = self.authorized_client2.get(reverse("follow_index"))
        follow_post = response2.context.get("page")
        self.assertNotEqual(follow_post, self.post)

    def test_user_can_follow(self):
        """Пользователь может подписываться"""
        self.authorized_client2.get(
            reverse("profile_follow",
                    kwargs={"username": self.user}))
        follows = Follow.objects.filter(
            user=self.user2, author=self.user).count()
        self.assertEqual(follows, 1)

    def test_user_can_unfollow(self):
        """Пользователь может отписываться"""
        self.authorized_client2.get(
            reverse("profile_unfollow",
                    kwargs={"username": self.user}))
        follows = Follow.objects.filter(
            user=self.user2, author=self.user).count()
        self.assertEqual(follows, 0)

    def cache_test(self):
        client = self.authorized_client
        response = client.get(reverse("index")).context.get("posts")[0].text
        self.assertEqual(response, "Тестовый текст")
        Post.objects.create(
            text="Тестовый текст 2",
            author=self.user,
            group=self.group.id,
        )
        response = client.get(reverse("index")).content.get("posts")[0].text
        self.assertEqual(response, "Тестовый текст")
        cache.clear()
        response = client.get(reverse("index")).content.get("index")[0].text
        self.assertNotEqual(response, "Тестовый текст")


class PaginatorViewsTest(TestCase):
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
        self.user = User.objects.create(username="tester")
        self.authorized_client = Client()
        self.authorized_client.force_login(self.user)

        for i in range(15):
            Post.objects.create(
                text=f"Тестовый текст{i}",
                author=self.user,
                pub_date="01.01.2020",
                group=self.group,
            )

    def test_two_pages_contain_fifteen_records(self):
        response = self.client.get(reverse("index"))
        self.assertEqual(len(response.context.get("page").object_list), 10)
        response = self.client.get(reverse("index") + "?page=2")
        self.assertEqual(len(response.context.get("page").object_list), 5)

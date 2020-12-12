import shutil
import tempfile
from django.conf import settings

from django.test import Client, TestCase
from django.test import override_settings

from django.core.files.uploadedfile import SimpleUploadedFile

from django.urls import reverse

from posts.models import Post, Group, User, Comment


class PostCreateFormTests(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.user = User.objects.create(username="tester")
        cls.authorized_client = Client()
        cls.authorized_client.force_login(cls.user)
        cls.group = Group.objects.create(
            title="Test group",
            slug="test",
            description="Тестовая группа"
        )
        cls.post = Post.objects.create(
            text="Тестовый текст",
            author=PostCreateFormTests.user,
            pub_date="01.01.2020",
            group=PostCreateFormTests.group,
        )

    @classmethod
    def tearDownClass(cls):
        # Рекурсивно удаляем временную после завершения тестов
        shutil.rmtree(settings.MEDIA_ROOT, ignore_errors=True)
        super().tearDownClass()

    @override_settings(MEDIA_ROOT=tempfile.gettempdir())
    def test_create_post(self):
        """Валидная форма создает запись в Post."""
        small_gif = (
            b'\x47\x49\x46\x38\x39\x61\x02\x00'
            b'\x01\x00\x80\x00\x00\x00\x00\x00'
            b'\xFF\xFF\xFF\x21\xF9\x04\x00\x00'
            b'\x00\x00\x00\x2C\x00\x00\x00\x00'
            b'\x02\x00\x01\x00\x00\x02\x02\x0C'
            b'\x0A\x00\x3B'
        )
        uploaded = SimpleUploadedFile(
            name="small.gif",
            content=small_gif,
            content_type="image/gif",
        )
        post_count = Post.objects.count()
        form_data = {
            "text": "Тестовый текст",
            "group": self.group.id,
            "image": uploaded,
        }
        response = self.authorized_client.post(
            reverse("new_post"),
            data=form_data,
            follow=True,
        )
        post = response.context["page"][0]
        self.assertEqual(Post.objects.count(), post_count + 1)
        self.assertEqual(post.text, form_data["text"])
        self.assertEqual(post.group.id, self.group.id)
        self.assertEqual(post.author, self.user)
        self.assertEqual(post.image.size, form_data["image"].size)
        self.assertRedirects(response, reverse("index"))

    def test_post_edit_can_change_post(self):
        """Пост редактируется"""
        post_count = Post.objects.count()
        form_data = {
            "text": "Тестовый текст 2",
            "group": self.group.id,
        }
        response = self.authorized_client.post(
            reverse("post_edit", args=[self.user, self.post.id]),
            data=form_data,
            follow=True,
        )
        post = Post.objects.last()
        self.assertEqual(200, response.status_code)
        self.assertRedirects(response, reverse(
            "post", args=[self.user, post.id]))
        self.assertEqual(post.text, form_data["text"])
        self.assertEqual(Post.objects.count(), post_count)

    def test_add_comment(self):
        comment_count = Comment.objects.count()
        form_data = {
            "author": self.user,
            "post": self.post,
            "text": "Comment test",
        }
        response = self.authorized_client.post(
            reverse("add_comment", kwargs={
                "username": self.post.author.username,
                "post_id": self.post.id
            }), data=form_data, follow=True,)
        comment = response.context["comments"].last()
        self.assertRedirects(response, reverse(
            "post", args=[self.user, self.post.id]))
        self.assertEqual(Comment.objects.count(), comment_count + 1)
        self.assertEqual(comment.text, form_data["text"])
        self.assertEqual(comment.author, self.user)
        self.assertEqual(comment.post, self.post)

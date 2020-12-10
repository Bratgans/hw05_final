import shutil
import tempfile
from django.conf import settings

from django.test import Client, TestCase
from django.test import override_settings

from django.core.files.uploadedfile import SimpleUploadedFile

from django.urls import reverse

from posts.models import Post, Group, User


class PostCreateFormTests(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        settings.MEDIA_ROOT = tempfile.mkdtemp(dir=settings.BASE_DIR)
        cls.user = User.objects.create(username="tester")
        cls.authorized_client = Client()
        cls.authorized_client.force_login(cls.user)
        cls.group = Group.objects.create(
            title="Test group",
            slug="test",
            description="Тестовая группа"
        )

    @classmethod
    def tearDownClass(cls):
        # Рекурсивно удаляем временную после завершения тестов
        shutil.rmtree(settings.MEDIA_ROOT, ignore_errors=True)
        super().tearDownClass()

    def test_create_post(self):
        """Валидная форма создает запись в Post."""
        form_data = {
            "text": "Тестовый текст",
            "group": self.group.id,
        }
        response = self.authorized_client.post(
            reverse("new_post"),
            data=form_data,
            follow=True,
        )
        post = Post.objects.first()
        self.assertRedirects(response, reverse("index"))
        self.assertEqual(Post.objects.count(), 1)
        self.assertEqual(post.text, form_data["text"])
        self.assertEqual(post.group.id, self.group.id)
        self.assertEqual(post.author, self.user)

    def test_post_edit_can_change_post(self):
        """Пост редактируется"""
        post = Post.objects.create(
            text="Тестовый текст",
            author=self.user,
            group=self.group,
            )
        post_count = Post.objects.count()
        form_data = {
            "text": "Тестовый текст 2",
            "group": self.group.id,
        }
        response = self.authorized_client.post(
            reverse("post_edit", args=[self.user, post.id]),
            data=form_data,
            follow=True,
        )
        post = Post.objects.last()
        self.assertEqual(200, response.status_code)
        self.assertRedirects(response, reverse("post",
                                               args=[self.user, post.id]))
        self.assertEqual(post.text, form_data['text'])
        self.assertEqual(Post.objects.count(), post_count)

    @override_settings(MEDIA_ROOT=tempfile.gettempdir())
    def test_new_post_creates_post_with_image(self):
        posts_count = Post.objects.count()
        small_gif = (
            b'\x47\x49\x46\x38\x39\x61\x02\x00'
            b'\x01\x00\x80\x00\x00\x00\x00\x00'
            b'\xFF\xFF\xFF\x21\xF9\x04\x00\x00'
            b'\x00\x00\x00\x2C\x00\x00\x00\x00'
            b'\x02\x00\x01\x00\x00\x02\x02\x0C'
            b'\x0A\x00\x3B'
        )
        uploaded = SimpleUploadedFile(
            name='small.gif',
            content=small_gif,
            content_type='image/gif'
        )
        form_data = {
            'text': "Image test",
            'group': self.group.id,
            'image': uploaded,
        }
        self.authorized_client.post(
            reverse('new_post'),
            data=form_data,
            follow=True
        )
        self.assertEqual(Post.objects.count(), posts_count+1)

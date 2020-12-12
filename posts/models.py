from django.db import models

from django.contrib.auth import get_user_model

User = get_user_model()


class Group(models.Model):
    title = models.CharField(max_length=200)
    slug = models.SlugField(unique=True, max_length=50)
    description = models.TextField()

    def __str__(self):
        return self.title


class Post(models.Model):
    text = models.TextField(verbose_name="Текст поста",
                            help_text="Введите текст сообщения")
    pub_date = models.DateTimeField("date published", 
                                    auto_now_add=True, 
                                    db_index=True)
    author = models.ForeignKey(User, on_delete=models.CASCADE,
                               related_name="posts")
    group = models.ForeignKey(Group, verbose_name="Сообщество",
                              help_text="Выберите Сообщество",
                              on_delete=models.SET_NULL,
                              related_name="posts", blank=True, null=True)
    image = models.ImageField(upload_to='posts/', blank=True, null=True)

    class Meta:
        ordering = ("-pub_date",)

    def __str__(self):
        return self.text[:15]


class Comment(models.Model):
    post = models.ForeignKey(Post, on_delete=models.CASCADE,
                             related_name="comments")
    author = models.ForeignKey(User, on_delete=models.CASCADE,
                               related_name="comments")
    text = models.TextField(verbose_name="Текст комментария",
                            help_text="Введите текст комментария")
    created = models.DateTimeField("date published", auto_now_add=True)

    class Meta:
        ordering = ("-created",)

    def __str__(self):
        return self.text[:15]


class Follow(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE,
                             related_name="follower")
    author = models.ForeignKey(User, on_delete=models.CASCADE,
                               related_name="following")
    
    class Meta:
        constraints = [models.UniqueConstraint(
            fields=['user', 'author'], name='unique_follows'
            )
        ]

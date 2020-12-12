from django.core.paginator import Paginator
from django.core.exceptions import ObjectDoesNotExist
from django.shortcuts import redirect, render, get_object_or_404
from django.contrib.auth.decorators import login_required

from .forms import PostForm, CommentForm

from .models import Post, Group, User, Follow


def index(request):
    post_list = Post.objects.select_related("group")
    paginator = Paginator(post_list, 10)
    page_number = request.GET.get("page")
    page = paginator.get_page(page_number)
    return render(
         request,
         "index.html",
         {"page": page,
          "paginator": paginator,
          }
    )


def group_posts(request, slug):
    group = get_object_or_404(Group, slug=slug)
    post_list = group.posts.all()
    paginator = Paginator(post_list, 10)
    page_number = request.GET.get("page")
    page = paginator.get_page(page_number)
    return render(
        request,
        "group.html",
        {"group": group,
         "page": page,
         "paginator": paginator,
         }
    )


@login_required
def new_post(request):
    form = PostForm(request.POST or None, files=request.FILES or None)
    if form.is_valid():
        new_form = form.save(commit=False)
        new_form.author = request.user
        new_form.save()
        return redirect("index")
    return render(request, "new.html", {"form": form})


def profile(request, username):
    author = get_object_or_404(User, username=username)
    posts = author.posts.all()
    paginator = Paginator(posts, 10)
    page_number = request.GET.get("page")
    page = paginator.get_page(page_number)
    followers = author.following.count()
    follows = author.follower.count()
    following = request.user.is_authenticated and Follow.objects.filter(
        author=author.id,
        user=request.user.id).exists()
    return render(request, 'profile.html', {
            'author': author,
            'page': page,
            'paginator': paginator,
            'followers': followers,
            'follows': follows,
            'following': following,
        })


def post_view(request, username, post_id):
    post = get_object_or_404(Post, id=post_id, author__username=username)
    post_comments = post.comments.all()
    form = CommentForm()
    return render(request,
                  "post.html",
                  {"author": post.author,
                   "post": post,
                   "comments": post_comments,
                   "form": form,
                   }
                  )


@login_required
def post_edit(request, username, post_id):
    post = get_object_or_404(Post, id=post_id, author__username=username)
    if request.user != post.author:
        return redirect("post", username=username, post_id=post_id)
    form = PostForm(request.POST or None,
                    files=request.FILES or None, instance=post)
    if form.is_valid():
        form.save()
        return redirect("post", username=username, post_id=post_id)
    return render(request,
                  "new.html",
                  {"form": form,
                   "post": post,
                   }
                  )


@login_required
def add_comment(request, username, post_id):
    post = get_object_or_404(Post, id=post_id, author__username=username)
    author = post.author
    form = CommentForm(request.POST or None)
    if not form.is_valid():
        return render(request, "post.html",
                      {"form": form,
                       "author": author,
                       "post": post})
    new_comment = form.save(commit=False)
    new_comment.author_id = request.user.id
    new_comment.post_id = post.id
    new_comment.save()
    return redirect("post", username, post_id)


@login_required
def follow_index(request):
    post_list = Post.objects.filter(author__following__user=request.user)
    paginator = Paginator(post_list, 10)
    page_number = request.GET.get("page")
    page = paginator.get_page(page_number)
    return render(
         request,
         "follow.html",
         {"page": page,
          "paginator": paginator,
          }
    )


@login_required
def profile_follow(request, username):
    author = get_object_or_404(User, username=username)
    if request.user != author:
        Follow.objects.get_or_create(
            user=request.user,
            author=author,
        )
    return redirect("profile", username)


@login_required
def profile_unfollow(request, username):
    author = get_object_or_404(User, username=username)
    unfollow = Follow.objects.filter(user=request.user,
                                     author=author or None)
    if unfollow.exists():
        unfollow.delete()
    return redirect("profile", username)


def page_not_found(request, exception):
    return render(
        request,
        "misc/404.html",
        {"path": request.path},
        status=404
    )


def server_error(request):
    return render(request, "misc/500.html", status=500)

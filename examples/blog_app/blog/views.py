"""Views demonstrating complex queries with django-libsql."""

from django.shortcuts import render, get_object_or_404
from django.db.models import Count, Q, Prefetch, F, Max
from django.core.paginator import Paginator
from django.utils import timezone
from django.views.decorators.cache import cache_page
from django.http import JsonResponse
from django.db import OperationalError
from .models import Post, Category, Tag, Comment, PostView


def index(request):
    """Homepage with latest posts and stats."""
    # Complex query with multiple relationships
    posts = (
        Post.objects.filter(status="published", published_date__lte=timezone.now())
        .select_related("author__user", "category")
        .prefetch_related(
            "tags",
            Prefetch(
                "comments",
                queryset=Comment.objects.filter(is_approved=True),
                to_attr="approved_comments",
            ),
        )
        .annotate(
            comment_total=Count("comments", filter=Q(comments__is_approved=True)),
            reply_count=Count(
                "comments__replies", filter=Q(comments__replies__is_approved=True)
            ),
        )
        .order_by("-published_date")[:5]
    )

    # Popular posts by view count
    popular_posts = (
        Post.objects.filter(status="published")
        .select_related("author__user")
        .order_by("-view_count")[:5]
    )

    # Categories with post counts
    categories = Category.objects.annotate(
        post_count=Count("posts", filter=Q(posts__status="published"))
    ).filter(post_count__gt=0)

    # Popular tags
    popular_tags = Tag.objects.annotate(
        post_count=Count("posts", filter=Q(posts__status="published"))
    ).order_by("-post_count")[:10]

    # Get recent comments
    recent_comments = (
        Comment.objects.filter(is_approved=True)
        .select_related("post")
        .order_by("-created_at")[:5]
    )
    
    context = {
        "posts": posts,
        "popular_posts": popular_posts,
        "categories": categories,
        "popular_tags": popular_tags,
        "recent_comments": recent_comments,
        "stats": {
            "posts": Post.objects.filter(status="published").count(),
            "authors": Post.objects.filter(status="published")
            .values("author")
            .distinct()
            .count(),
            "comments": Comment.objects.filter(is_approved=True).count(),
            "categories": Category.objects.count(),
        },
    }

    return render(request, "blog/index.html", context)


def post_detail(request, slug):
    """Post detail with comments and related posts."""
    post = get_object_or_404(
        Post.objects.select_related("author__user", "category").prefetch_related(
            "tags",
            Prefetch(
                "comments",
                queryset=Comment.objects.filter(is_approved=True, parent=None)
                .prefetch_related("replies")
                .order_by("-created_at"),
            ),
        ),
        slug=slug,
        status="published",
    )

    # Increment view count
    post.view_count = F("view_count") + 1
    post.save(update_fields=["view_count"])

    # Track detailed view
    PostView.objects.create(
        post=post,
        ip_address=request.META.get("REMOTE_ADDR", "0.0.0.0"),
        user_agent=request.META.get("HTTP_USER_AGENT", ""),
        referrer=request.META.get("HTTP_REFERER", ""),
    )

    # Related posts (same category or tags)
    related_posts = (
        Post.objects.filter(
            Q(category=post.category) | Q(tags__in=post.tags.all()),
            status="published",
        )
        .exclude(id=post.id)
        .distinct()
        .select_related("author__user")[:5]
    )

    context = {
        "post": post,
        "related_posts": related_posts,
    }

    return render(request, "blog/post_detail.html", context)


def category_posts(request, slug):
    """Posts by category with pagination."""
    category = get_object_or_404(Category, slug=slug)

    # Include posts from subcategories
    categories = [category] + list(category.children.all())

    posts = (
        Post.objects.filter(
            category__in=categories,
            status="published",
            published_date__lte=timezone.now(),
        )
        .select_related("author__user", "category")
        .prefetch_related("tags")
        .annotate(comment_total=Count("comments", filter=Q(comments__is_approved=True)))
        .order_by("-published_date")
    )

    paginator = Paginator(posts, 10)
    page = request.GET.get("page")
    posts_page = paginator.get_page(page)

    context = {
        "category": category,
        "posts": posts_page,
        "subcategories": category.children.annotate(
            post_count=Count("posts", filter=Q(posts__status="published"))
        ),
    }

    return render(request, "blog/category_posts.html", context)


def search(request):
    """Search posts with full-text search simulation."""
    query = request.GET.get("q", "")

    if query:
        # Simulate full-text search with multiple fields
        posts = (
            Post.objects.filter(
                Q(title__icontains=query)
                | Q(content__icontains=query)
                | Q(excerpt__icontains=query)
                | Q(tags__name__icontains=query)
                | Q(category__name__icontains=query)
                | Q(author__user__username__icontains=query),
                status="published",
            )
            .distinct()
            .select_related("author__user", "category")
            .prefetch_related("tags")
            .order_by("-published_date")
        )
    else:
        posts = Post.objects.none()

    paginator = Paginator(posts, 10)
    page = request.GET.get("page")
    posts_page = paginator.get_page(page)

    context = {
        "query": query,
        "posts": posts_page,
        "result_count": posts.count(),
    }

    return render(request, "blog/search.html", context)


@cache_page(60 * 5)  # Cache for 5 minutes
def api_posts(request):
    """API endpoint demonstrating JSON serialization."""
    posts = (
        Post.objects.filter(status="published", published_date__lte=timezone.now())
        .select_related("author__user", "category")
        .prefetch_related("tags")
        .values(
            "id",
            "title",
            "slug",
            "excerpt",
            "published_date",
            "view_count",
            "author__user__username",
            "author__user__first_name",
            "author__user__last_name",
            "category__name",
            "category__slug",
        )
        .annotate(
            comment_total=Count("comments", filter=Q(comments__is_approved=True)),
            tag_list=Count("tags"),
        )
        .order_by("-published_date")[:20]
    )

    # Convert to list and add tags
    posts_list = []
    for post in posts:
        post_dict = dict(post)
        # Get tags for this post
        tags = Tag.objects.filter(posts__id=post["id"]).values_list("name", flat=True)
        post_dict["tags"] = list(tags)
        posts_list.append(post_dict)

    return JsonResponse(
        {
            "posts": posts_list,
            "count": len(posts_list),
            "timestamp": timezone.now().isoformat(),
        }
    )

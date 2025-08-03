"""Create sample data for blog app."""

from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from django.utils import timezone
from django.utils.text import slugify
from datetime import timedelta
import random
import lorem

from blog.models import Author, Category, Tag, Post, Comment


class Command(BaseCommand):
    help = "Creates sample blog data with posts, categories, tags, and comments"

    def handle(self, *args, **options):
        self.stdout.write("Creating sample blog data...")

        # Create users and authors
        users_data = [
            {
                "username": "john_doe",
                "first_name": "John",
                "last_name": "Doe",
                "email": "john@example.com",
            },
            {
                "username": "jane_smith",
                "first_name": "Jane",
                "last_name": "Smith",
                "email": "jane@example.com",
            },
            {
                "username": "tech_writer",
                "first_name": "Tech",
                "last_name": "Writer",
                "email": "tech@example.com",
            },
        ]

        authors = []
        for user_data in users_data:
            user, created = User.objects.get_or_create(
                username=user_data["username"],
                defaults={
                    "first_name": user_data["first_name"],
                    "last_name": user_data["last_name"],
                    "email": user_data["email"],
                },
            )
            if created:
                user.set_password("password123")
                user.save()

            author, _ = Author.objects.get_or_create(
                user=user,
                defaults={
                    "bio": f"{user.first_name} is a passionate writer and blogger.",
                    "website": f"https://{user.username}.example.com",
                    "twitter_handle": f"@{user.username}",
                },
            )
            authors.append(author)
            self.stdout.write(f"Created author: {author}")

        # Create categories
        categories_data = [
            {"name": "Technology", "description": "Latest tech news and tutorials"},
            {
                "name": "Programming",
                "description": "Programming tutorials and best practices",
                "parent": "Technology",
            },
            {
                "name": "Web Development",
                "description": "Web development tips and tricks",
                "parent": "Programming",
            },
            {
                "name": "Python",
                "description": "Python programming language",
                "parent": "Programming",
            },
            {
                "name": "Django",
                "description": "Django web framework",
                "parent": "Python",
            },
            {"name": "Lifestyle", "description": "Lifestyle and personal development"},
            {"name": "Travel", "description": "Travel guides and experiences"},
        ]

        created_categories = {}
        for cat_data in categories_data:
            parent = None
            if "parent" in cat_data:
                parent = created_categories.get(cat_data["parent"])

            category, _ = Category.objects.get_or_create(
                name=cat_data["name"],
                defaults={
                    "slug": slugify(cat_data["name"]),
                    "description": cat_data["description"],
                    "parent": parent,
                },
            )
            created_categories[cat_data["name"]] = category
            self.stdout.write(f"Created category: {category.name}")

        # Create tags
        tag_names = [
            "tutorial",
            "beginner",
            "advanced",
            "tips",
            "best-practices",
            "news",
            "update",
            "guide",
            "how-to",
            "review",
            "django",
            "python",
            "javascript",
            "css",
            "html",
            "database",
            "api",
            "security",
            "performance",
            "testing",
        ]

        tags = []
        for tag_name in tag_names:
            tag, _ = Tag.objects.get_or_create(
                name=tag_name, defaults={"slug": slugify(tag_name)}
            )
            tags.append(tag)

        # Create posts
        post_templates = [
            {
                "title": "Getting Started with Django and LibSQL",
                "category": "Django",
                "tags": ["django", "tutorial", "beginner", "database"],
                "status": "published",
            },
            {
                "title": "Building Real-time Applications with Turso",
                "category": "Web Development",
                "tags": ["tutorial", "database", "performance", "api"],
                "status": "published",
            },
            {
                "title": "Python 3.13 No-GIL: Performance Breakthrough",
                "category": "Python",
                "tags": ["python", "performance", "news", "advanced"],
                "status": "published",
            },
            {
                "title": "10 Django Security Best Practices",
                "category": "Django",
                "tags": ["django", "security", "best-practices", "guide"],
                "status": "published",
            },
            {
                "title": "My Journey Learning Web Development",
                "category": "Lifestyle",
                "tags": ["beginner", "guide", "tips"],
                "status": "published",
            },
            {
                "title": "Draft: Upcoming Features in Django 5.3",
                "category": "Django",
                "tags": ["django", "news", "update"],
                "status": "draft",
            },
        ]

        posts = []
        for i, post_data in enumerate(post_templates):
            # Vary publication dates
            days_ago = random.randint(1, 30)
            published_date = (
                timezone.now() - timedelta(days=days_ago)
                if post_data["status"] == "published"
                else None
            )

            post = Post.objects.create(
                title=post_data["title"],
                slug=slugify(post_data["title"]),
                author=random.choice(authors),
                category=created_categories[post_data["category"]],
                content="\n\n".join(
                    [lorem.paragraph() for _ in range(random.randint(5, 10))]
                ),
                excerpt=lorem.paragraph()[:200] + "...",
                status=post_data["status"],
                published_date=published_date,
                view_count=random.randint(10, 1000)
                if post_data["status"] == "published"
                else 0,
            )

            # Add tags
            post_tags = [tag for tag in tags if tag.name in post_data["tags"]]
            post.tags.set(post_tags)

            posts.append(post)
            self.stdout.write(f"Created post: {post.title}")

        # Create comments on published posts
        published_posts = [p for p in posts if p.status == "published"]

        for post in published_posts:
            # Create 0-5 comments per post
            num_comments = random.randint(0, 5)

            for j in range(num_comments):
                comment = Comment.objects.create(
                    post=post,
                    author_name=f"Reader {random.randint(1, 100)}",
                    author_email=f"reader{random.randint(1, 100)}@example.com",
                    content=lorem.paragraph(),
                    is_approved=random.random() > 0.2,  # 80% approved
                )

                # Some comments have replies
                if random.random() < 0.3 and comment.is_approved:
                    Comment.objects.create(
                        post=post,
                        author_name=random.choice(authors).user.get_full_name(),
                        author_email=random.choice(authors).user.email,
                        content="Thanks for your comment! " + lorem.sentence(),
                        parent=comment,
                        is_approved=True,
                    )

        # Summary
        self.stdout.write(
            self.style.SUCCESS(
                f"\nSuccessfully created sample blog data:\n"
                f"- {len(authors)} authors\n"
                f"- {len(created_categories)} categories\n"
                f"- {len(tags)} tags\n"
                f"- {Post.objects.count()} posts\n"
                f"- {Comment.objects.count()} comments"
            )
        )

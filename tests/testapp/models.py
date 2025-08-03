from django.db import models


class TestModel(models.Model):
    name = models.CharField(max_length=100)
    value = models.IntegerField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        app_label = "testapp"


class RelatedModel(models.Model):
    test_model = models.ForeignKey(TestModel, on_delete=models.CASCADE)
    description = models.TextField()

    class Meta:
        app_label = "testapp"


class Book(models.Model):
    title = models.CharField(max_length=200)
    author = models.CharField(max_length=100)
    isbn = models.CharField(max_length=13, unique=True)
    published_date = models.DateField()
    pages = models.IntegerField()
    price = models.DecimalField(max_digits=10, decimal_places=2)
    in_stock = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        app_label = "testapp"
        ordering = ["-published_date"]
        indexes = [
            models.Index(fields=["isbn"]),
            models.Index(fields=["author", "title"]),
        ]

    def __str__(self):
        return f"{self.title} by {self.author}"


class Review(models.Model):
    book = models.ForeignKey(Book, on_delete=models.CASCADE, related_name="reviews")
    reviewer_name = models.CharField(max_length=100)
    rating = models.IntegerField(choices=[(i, i) for i in range(1, 6)])
    comment = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        app_label = "testapp"
        ordering = ["-created_at"]
        unique_together = ["book", "reviewer_name"]

    def __str__(self):
        return f"{self.reviewer_name}'s review of {self.book.title}"

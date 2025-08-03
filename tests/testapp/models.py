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
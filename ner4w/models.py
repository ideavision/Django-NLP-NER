from django.db import models
from django.contrib.auth.models import User

class Report(models.Model):
    SOURCE = (
        ('File', 'File'),
        ('Twitter', 'Twitter')
    )
    text = models.TextField(max_length=5000, null=True)
    source = models.CharField(max_length=25 , null=True, choices=SOURCE)
    what = models.CharField(max_length=250)
    when = models.CharField(max_length=250)
    where = models.CharField(max_length=250)
    who = models.CharField(max_length=250)
    user = models.ForeignKey(User, on_delete=models.CASCADE)

    def __str__(self):
        return self.text

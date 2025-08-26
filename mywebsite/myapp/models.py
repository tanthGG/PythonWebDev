from django.db import models

# Create your models here.

class Product(models.Model):
    title = models.CharField(max_length=200)
    description = models.TextField(null=True, blank=True)
    price = models.DecimalField(max_digits=10, decimal_places=2, \
                                null=True, blank=True)
    quantity = models.IntegerField(default=0, null=True, blank=True)
    instock = models.BooleanField(default=True)

    def __str__(self):
        return self.title
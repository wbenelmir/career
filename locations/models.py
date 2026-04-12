# locations/models.py
from django.db import models

class Wilaya(models.Model):
    code = models.CharField(max_length=2, unique=True)
    name_fr = models.CharField(max_length=100)
    name_ar = models.CharField(max_length=100)

    class Meta:
        ordering = ["code"]

    def __str__(self):
        return f"{self.code} - {self.name_fr}"


class Commune(models.Model):
    code = models.CharField(max_length=10, blank=False, null=False)    
    wilaya = models.ForeignKey(Wilaya, on_delete=models.PROTECT, related_name="communes")
    name_fr = models.CharField(max_length=120)
    name_ar = models.CharField(max_length=120, blank=True, null=True)  # optional
    
    class Meta:
        ordering = ["wilaya__code", "name_fr"]
        unique_together = ("wilaya", "name_fr")

    def __str__(self):
        return f"{self.wilaya.code} - {self.name_fr}"
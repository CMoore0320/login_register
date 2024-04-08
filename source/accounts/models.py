from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone


class Activation(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)
    code = models.CharField(max_length=20, unique=True)
    email = models.EmailField(blank=True)

    def __str__(self):
        return self.user.username
    

######################## Everything below is additional for my project  ##############################


class Address(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    address = models.CharField(max_length= 100, unique=False)

    def __str__(self):
        return self.address
    

class Equipment(models.Model):
    address = models.ForeignKey(Address, on_delete=models.CASCADE )
    component = models.CharField(max_length=150, unique=False)
    frequency = models.IntegerField()
    description = models.CharField(max_length=50, unique=False, default='Replace')

    class Meta:
        unique_together = (('address', 'component','description'),)

    def __str__(self):
        return self.component
    


class Maintenance(models.Model):
    component = models.ForeignKey(Equipment, on_delete=models.CASCADE)
    dateCompleted = models.DateField(default = timezone.now)
    maintenance_price = models.DecimalField(max_digits =10, decimal_places=2, default=0.00)
    notes = models.CharField(max_length=300, blank=True, default="No Notes")

    class Meta:
        unique_together = (('component', 'dateCompleted','maintenance_price'),)

    def __str__(self):
        return self.component + ' ' + self.dateCompleted


class Receipt(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    address = models.ForeignKey(Address, on_delete=models.CASCADE)
    component = models.CharField(max_length=150)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    date = models.DateField()
    image = models.ImageField(upload_to='receipt_images/')

    def __str__(self):
        return f"{self.component} - {self.address}"    
from django.db import models
from django.contrib.auth.models import User


# Create your models here.
class Team(models.Model):
    name = models.CharField(max_length=30)
    description = models.TextField(blank="True", null="True")
    logo = models.ImageField(blank="True", null="True")
    location = models.CharField(max_length=40, blank="True", null="True")

    def __str__(self):
        return self.name


class Match(models.Model):
    RESULTS = (
        ('NR', 'No Results'),
        ('team1', 'Team1'),
        ('team2', 'Team2'),
        ('IP', 'In Progress'),
        ('TBD', 'TBD')
    )
    team1 = models.ForeignKey(Team, on_delete=models.SET_NULL, null="True", related_name='team1')
    team2 = models.ForeignKey(Team, on_delete=models.SET_NULL, null="True", related_name='team2')
    description = models.TextField( blank="True", null="True")
    venue = models.CharField(max_length=40, blank="True", null="True")
    result = models.CharField(max_length=10, choices=RESULTS ,default="TBD")
    datetime = models.DateTimeField()
    tournaments = models.CharField(max_length=50, default="IPL", blank="True", null="True")

    def __str__(self):
        return self.description


class Selection(models.Model):
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null="True")
    match = models.ForeignKey(Match, on_delete=models.SET_NULL, null="True")
    selection = models.ForeignKey(Team, on_delete=models.SET_NULL, null="True")



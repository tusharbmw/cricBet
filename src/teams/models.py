from django.db import models
from django.contrib.auth.models import User


# Create your models here.
class Team(models.Model):
    name = models.CharField(max_length=30)
    description = models.TextField(blank="True", null="True")
    logo = models.ImageField(blank="True", null="True")
    location = models.CharField(max_length=40, blank="True", null="True")
    logo_url = models.CharField(max_length=100, blank="True", null="True")

    def __str__(self):
        return self.name


class Match(models.Model):
    RESULTS = (
        ('NR', 'No Results'),
        ('team1', 'Team1'),
        ('team2', 'Team2'),
        ('IP', 'In Progress'),
        ('TBD', 'TBD'),
        ('TOSS', 'Toss'),
        ('DLD', 'Delayed'),
    )
    team1 = models.ForeignKey(Team, on_delete=models.SET_NULL, null="True", related_name='team1')
    team2 = models.ForeignKey(Team, on_delete=models.SET_NULL, null="True", related_name='team2')
    description = models.TextField( blank="True", null="True")
    venue = models.CharField(max_length=40, blank="True", null="True")
    result = models.CharField(max_length=10, choices=RESULTS ,default="TBD")
    datetime = models.DateTimeField()
    tournament = models.CharField(max_length=50, default="IPL", blank="True", null="True")
    match_id = models.CharField(max_length=50, blank="True", null="True")
    match_points = models.IntegerField(default=1)

    def __str__(self):
        return self.description


class Selection(models.Model):
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null="True")
    match = models.ForeignKey(Match, on_delete=models.SET_NULL, null="True")
    selection = models.ForeignKey(Team, on_delete=models.SET_NULL, null="True")
    hidden = models.BooleanField(default=False)



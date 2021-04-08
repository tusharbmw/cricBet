from django.contrib import admin

# Register your models here.
from .models import Team, Match, Selection
admin.site.register(Team)
admin.site.register(Match)
admin.site.register(Selection)
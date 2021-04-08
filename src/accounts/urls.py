from django.urls import path
from . import views


urlpatterns = [
    path('', views.schedule_view),
    path('contact/', views.contact),
    path('teams/', views.teams_view),
    path('login/', views.login_page, name='login'),
    path('logout/', views.logout_page, name='logout'),
    path('register/', views.register_page, name='register'),
    path('dashboard/', views.dashboard),
    path('schedule/<str:pk>', views.schedule_view),
    path('schedule/', views.schedule_view,name='schedule'),
    path('update/', views.update, name='update'),
]
from django.urls import path
from . import views

urlpatterns = [
	path('', views.index, name='index'),
	path('get_4w_event/', views.get_4w_event, name='get_4w_event'),
]
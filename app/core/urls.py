from django.urls import path
from . import views

urlpatterns = [
    # Health check
    path('health/', views.health_check, name='health'),
    
    # Public pages
    path('', views.landing_page, name='landing'),
    path('demo/', views.demo, name='demo'),
    
    # Authentication
    path('register/', views.register, name='register'),
    path('login/', views.user_login, name='login'),
    path('logout/', views.user_logout, name='logout'),
    
    # User dashboard and profile
    path('dashboard/', views.dashboard, name='dashboard'),
    path('profile/', views.profile, name='profile'),
    path('profile/password/', views.change_password, name='change_password'),
    path('profile/delete/', views.delete_account, name='delete_account'),
    
    # Credits
    path('credits/', views.credits, name='credits'),
    
    # Jobs
    path('jobs/', views.jobs_list, name='jobs_list'),
    path('jobs/new/', views.create_job, name='create_job'),
    path('jobs/<uuid:job_id>/', views.job_detail, name='job_detail'),
    path('jobs/<uuid:job_id>/status/', views.job_status_api, name='job_status_api'),
    path('jobs/<uuid:job_id>/download/<str:stem>/', views.download_stem, name='download_stem'),
    path('jobs/<uuid:job_id>/download-all/', views.download_all_stems, name='download_all_stems'),
    
    # Payments
    path('purchase/<int:package_id>/', views.purchase_credits, name='purchase_credits'),
    path('purchase/<int:package_id>/process/', views.process_payment, name='process_payment'),
]

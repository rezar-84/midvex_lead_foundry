from django.contrib import admin
from django.contrib.auth import views as auth_views
from django.urls import include, path, re_path

from foundry.api import api
from foundry.spa import spa_index

urlpatterns = [
    path("admin/", admin.site.urls),
    path(
        "accounts/login/",
        auth_views.LoginView.as_view(template_name="registration/login.html"),
        name="login",
    ),
    path("accounts/logout/", auth_views.LogoutView.as_view(), name="logout"),
    path("api/", api.urls),
    path("", include("foundry.urls")),
    # The SPA owns every path no earlier pattern claimed. Keep this last.
    re_path(r"^.*$", spa_index, name="spa_index"),
]

from django.http import HttpResponse


def login_view(request):
    return HttpResponse("Login view placeholder")


def logout_view(request):
    return HttpResponse("Logout view placeholder")


def profile_view(request):
    return HttpResponse("Profile view placeholder")

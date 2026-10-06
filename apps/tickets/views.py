from django.http import HttpResponse


def ticket_list(request):
    return HttpResponse("Ticket list placeholder")


def ticket_kanban(request):
    return HttpResponse("Ticket kanban placeholder")


def ticket_create(request):
    return HttpResponse("Ticket create placeholder")


def manage_routing(request):
    return HttpResponse("Manage routing placeholder")

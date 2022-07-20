from django.views.generic import (
    TemplateView,
    DetailView,
)
from fruitdb.models import *


class TestTemplateView(TemplateView):
    template_name = "ssdfdsf.html"


class PostDetailView(DetailView):
    template_name = "home_content.html"
    model = Post
    # context_object_name = "object"
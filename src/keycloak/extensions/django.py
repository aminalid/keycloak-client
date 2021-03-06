# -*- coding: utf-8 -*-
import json
from typing import Callable

from django.conf import settings
from django.http import HttpRequest, HttpResponse, HttpResponseRedirect
from keycloak import Client


class AuthenticationMiddleware:
    def __init__(self, get_response: Callable):
        self.get_response = get_response
        self.kc = Client(self.callback_uri)

    @property
    def redirect_uri(self) -> str:
        return settings.KEYCLOAK_REDIRECT_URI

    @property
    def callback_uri(self) -> str:
        return settings.KEYCLOAK_CALLBACK_URI

    def callback(self, request: HttpRequest) -> HttpResponse:

        # validate state
        state = request.GET.get("state", "unknown")
        _state = request.session.pop("state", None)
        if state != _state:
            return HttpResponse("Invalid state", status=403)

        # fetch user tokens
        code: str = request.GET.get("code", "unknown")
        tokens = self.kc.callback(code)
        request.session["tokens"] = json.dumps(tokens)

        # fetch user info
        access_token = tokens["access_token"]
        user = self.kc.userinfo(access_token)
        request.session["user"] = json.dumps(user)

        return HttpResponseRedirect(self.redirect_uri)

    def login(self, request: HttpRequest) -> HttpResponse:
        """ Initiate authentication """
        url, state = self.kc.login()
        request.session["state"] = state
        return HttpResponseRedirect(url)

    def __call__(self, request: HttpRequest) -> HttpResponse:

        # handle callback requests
        if request.path == "/kc/callback":
            return self.callback(request)

        # handle unauthorized requests
        if "user" not in request.session:
            return self.login(request)

        # handle authorized requests
        return self.get_response(request)

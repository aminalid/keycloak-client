# -*- coding: utf-8 -*-
import base64
import json
import logging
from typing import List, Tuple

import jwt
import requests
from jwt import algorithms
from cached_property import cached_property_with_ttl

from ..config import config
from ..constants import Logger, Algorithms
from ..utils import fix_padding


log = logging.getLogger(Logger.name)


class JWTMixin:
    """ This class consists of methods that can be user to perform JWT operations """

    @cached_property_with_ttl(ttl=86400)
    def _keys(self) -> List:
        log.info("Retrieving keys from keycloak server")
        response = requests.get(config.uma2.jwks_uri)
        response.raise_for_status()
        return response.json().get("keys", [])

    def _jwk(self, kid) -> str:
        for key in self._keys:
            if key["kid"] == kid:
                return json.dumps(key)

    @staticmethod
    def _key(alg, jwk):
        if alg in Algorithms.ec:
            return algorithms.ECAlgorithm.from_jwk(jwk)
        if alg in Algorithms.hmac:
            return algorithms.HMACAlgorithm.from_jwk(jwk)
        if alg in Algorithms.rsa:
            return algorithms.RSAAlgorithm.from_jwk(jwk)
        if alg in Algorithms.rsapss:
            return algorithms.RSAPSSAlgorithm.from_jwk(jwk)

    def _parse_key_and_alg(self, header) -> Tuple:

        # decode header
        header = fix_padding(header)
        header = base64.b64decode(header)
        header = json.loads(header)

        # fetch jwk
        kid = header.get("kid")
        jwk = self._jwk(kid)

        # fetch key
        alg = header.get("alg")
        key = self._key(alg, jwk)

        return header, key, alg

    def decode(self, token: str) -> str:
        header, _, _ = token.split(".")
        _, key, algorithm = self._parse_key_and_alg(header)
        return jwt.decode(
            token,
            key,
            algorithms=[algorithm],
            issuer=config.uma2.issuer,
            audience=config.client.client_id,
        )
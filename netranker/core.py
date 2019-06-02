from datetime import datetime, timedelta

import jwt

class Pairing():

    def __init__(self, sampler):
        self.sampling_method = str(sampler)
        self.cards = sampler.sample(2)

    def issue_jwt(self, hmac_key):
        return jwt.encode(
            self.claims, hmac_key, algorithm='HS256'
        ).decode('utf-8')

    @property
    def claims(self):
        return {
            'cards': self.cards,
            'iat': datetime.utcnow(),
            'exp': datetime.utcnow() + timedelta(days=30)
        }

class Result():

    def __init__(self, winner, pairing, storage):
        self.winner = winner
        self.pairing = pairing
        self._storage = storage

    def register(self):
        self._storage.insert({
            'winner': self.winner,
            'pairing': self.pairing,
            'created_at': datetime.now()
        })

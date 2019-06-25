from datetime import datetime, timedelta
from collections import Counter

import jwt

class Pairing():

    def __init__(self, sampler):
        self.sampling_method = str(sampler)
        self.cards = sampler.sample(2)

    def issue_jwt(self, hmac_key):
        claims = {
            'cards': self.cards,
            'iat': datetime.utcnow(),
            'exp': datetime.utcnow() + timedelta(days=30)
        }
        return jwt.encode(
            claims, hmac_key, algorithm='HS256'
        ).decode('utf-8')

class Result():

    def __init__(self, winner, pairing, storage):
        if winner not in pairing['cards']:
            raise Exception
        self.winner = winner
        self.pairing = pairing
        self._storage = storage

        self._register()

    def _register(self):
        self._storage.insert_one({
            'winner': self.winner,
            'pairing': self.pairing,
            'created_at': datetime.now()
        })

def generate_ranking(storage):
    all_winners = [result['winner'] for result in storage.find()]
    winners_by_wins = [
        {
            'card': {
                'name': card,
                'faction': storage.lookup({'name': card})['faction']
            },
            'score': score
        }
        for card, score in Counter(all_winners).most_common()
    ]
    return winners_by_wins

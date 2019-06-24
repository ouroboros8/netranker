import unittest
from datetime import datetime, timedelta
from uuid import uuid4

import jwt
from pymongo import MongoClient

from netranker.app import app
import netranker.utils as utils
from netranker.samplers import SimpleRandom
from netranker.storage import MongoDbStorage

DB_NAME = 'netranker-test-%s' % uuid4()
app.config['DATABASE'] = DB_NAME

def setUpModule():
    utils.load_cards_from_disk(app.config['STORAGE'])

def tearDownModule():
    MongoClient().drop_database(DB_NAME)

class TestAppConfig(unittest.TestCase):

    def test_storage_backend_initialisation(self):
        self.assertIsInstance(app.config['STORAGE'], MongoDbStorage)
        self.assertIsInstance(app.config['SAMPLER'], SimpleRandom)

class TestVoting(unittest.TestCase):

    def setUp(self):
        self.client = app.test_client()

    def tearDown(self):
        app.config['STORAGE']._results.delete_many({})

    def test_get_new_pairing(self):
        response = self.client.get('/pairing')

        self.assertEqual(response.status_code, 200)

        self.assertEqual(response.headers['content-type'], 'application/json')

        cards = response.json.get('cards', None)
        self.assertEqual(len(cards), 2)
        for card in cards:
            self.assertEqual(type(card), str)

        token = response.json.get('token', None)
        try:
            claims = jwt.decode(token, app.config['HMAC_KEY'], algorithms=['HS256'])
        except jwt.DecodeError as exception:
            self.fail('Could not decode pairing jwt: %s' % exception)

        self.assertIn('exp', claims.keys())
        self.assertIn('iat', claims.keys())
        self.assertIn('cards', claims.keys())

    def test_submit_pairing(self):
        response = self.client.get('/pairing')

        headers = {'authorization': 'bearer ' + response.json.get('token')}
        result = {'winner': response.json.get('cards')[0]}

        response = self.client.post('/result', json=result, headers=headers)
        self.assertEqual(response.status_code, 204)

    def test_submit_pairing_without_winner(self):
        response = self.client.get('/pairing')

        headers = {'authorization': 'bearer ' + response.json.get('token')}
        result = {}

        response = self.client.post('/result', json=result, headers=headers)
        self.assertEqual(response.status_code, 400)

    def test_submit_pairing_without_token(self):
        response = self.client.get('/pairing')
        cards = response.json.get('cards', None)

        result = {'winner': cards[0]}

        response = self.client.post('/result', json=result)
        self.assertEqual(response.status_code, 403)

    def test_submit_pairing_with_invalid_token(self):
        response = self.client.get('/pairing')
        cards = response.json.get('cards', None)
        invalid_token = jwt.encode(
            {}, 'invalid_secret', algorithm='HS256'
        ).decode('utf-8')

        headers = {'authorization': 'bearer ' + invalid_token}
        result = {'winner': cards[0]}

        response = self.client.post('/result', json=result, headers=headers)
        self.assertEqual(response.status_code, 401)

    def test_submit_pairing_with_invalid_winner(self):
        response = self.client.get('/pairing')

        headers = {'authorization': 'bearer ' + response.json.get('token')}
        result = {'winner': 'The Shadow: Pulling the Strings'}

        response = self.client.post('/result', json=result, headers=headers)
        self.assertEqual(response.status_code, 401)

    def test_submit_pairing_with_expired_token(self):
        cards = ['Oversight AI', 'Melange Mining Corp.']
        expired_jwt = jwt.encode(
            {
                'exp': datetime.utcnow() - timedelta(days=30),
                'cards': cards
            },
            app.config['SIGNING_KEY'],
            algorithm='HS256'
        ).decode('utf-8')

        headers = {'authorization': 'bearer ' + expired_jwt}
        result = {'winner': cards[0]}

        response = self.client.post('/result', json=result, headers=headers)
        self.assertEqual(response.status_code, 401)

    def test_submit_pairing_with_invalid_auth_type(self):
        response = self.client.get('/pairing')
        cards = response.json.get('cards')

        headers = {'authorization': 'basic ' + response.json.get('token')}
        result = {'winner': cards[0]}

        response = self.client.post('/result', json=result, headers=headers)
        self.assertEqual(response.status_code, 401)

class TestProduceRanking(unittest.TestCase):

    def setUp(self):
        self.signing_key = 'test signing key'
        app.config['SIGNING_KEY'] = self.signing_key
        self.client = app.test_client()

    def tearDown(self):
        app.config['STORAGE']._results.delete_many({})

    def test_empty_ranking(self):
        result = self.client.get('/ranking')
        self.assertEqual(result.status_code, 200)
        self.assertEqual(result.json, {'ranking': []})

    def test_single_result_ranking(self):
        response = self.client.get('/pairing')
        headers = {'authorization': 'bearer ' + response.json.get('token')}
        winner = response.json.get('cards')[0]
        response = self.client.post('/result', json={'winner': winner},
                                    headers=headers)

        result = self.client.get('/ranking')
        self.assertEqual(result.status_code, 200)

        winner_faction = app.config['STORAGE'].lookup(
            {'name': winner}
        )['faction']

        ranking = {
            'ranking': [
                {
                    'card': {
                        'name': winner,
                        'faction': winner_faction
                    },
                    'score': 1
                }
            ]
        }
        self.assertEqual(result.json, ranking)

    def test_multiple_result_ranking(self):
        results = [
            {
                'winner': 'AstroScript Pilot Program',

                'claims': {
                    'cards': ['AstroScript Pilot Program', 'Philotic Entanglement'],
                    'iat': datetime.now() - timedelta(minutes=5),
                    'exp': datetime.now() - timedelta(minutes=5) + timedelta(days=30)
                }
            },
            {
                'winner': 'AstroScript Pilot Program',
                'claims': {
                    'cards': ['AstroScript Pilot Program', 'Philotic Entanglement'],
                    'iat': datetime.now() - timedelta(minutes=5),
                    'exp': datetime.now() - timedelta(minutes=5) + timedelta(days=30)
                }
            },
            {
                'winner': 'Philotic Entanglement',
                'claims': {
                    'cards': ['Philotic Entanglement', 'Toshiyuki Sakai'],
                    'iat': datetime.now() - timedelta(minutes=5),
                    'exp': datetime.now() - timedelta(minutes=5) + timedelta(days=30)
                }
            }
        ]

        for result in results:
            headers = {
                'authorization': 'bearer ' + jwt.encode(
                    result['claims'], app.config['HMAC_KEY'], algorithm='HS256'
                ).decode('utf-8')
            }
            self.client.post(
                '/result', json={'winner': result['winner']}, headers=headers
            )

        result = self.client.get('/ranking')
        self.assertEqual(result.status_code, 200)

        expected_ranking = {
            'ranking': [
                {
                    'score': 2,
                    'card': {
                        'name': 'AstroScript Pilot Program',
                        'faction': 'nbn',
                    }
                },
                {
                    'score': 1,
                    'card': {
                        'name': 'Philotic Entanglement',
                        'faction': 'jinteki',
                    }
                },
            ]
        }
        self.assertEqual(result.json, expected_ranking)

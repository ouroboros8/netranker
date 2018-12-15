import unittest

from netranker.core import Pairing

from netranker.ports import CardSampler

class TestPairing(unittest.TestCase):

    def test_init(self):
        '''
        Test that Pairings initialise correctly with a UUID and a pair of cards
        '''
        pairing = Pairing()

        self.assertTrue(hasattr(pairing, 'uuid'))
        self.assertTrue(hasattr(pairing, 'cards'))

        self.assertEqual(len(pairing.cards), 2)

    def test_uniqueness(self):
        '''
        Test that the UUIDs on two different Pairings are unique, and that each
        Pairing is of two unique cards.
        '''
        pair1 = Pairing()
        pair2 = Pairing()

        self.assertNotEqual(pair1.uuid, pair2.uuid)
        self.assertNotEqual(pair1.uuid, pair2.uuid)

        # need to implement card fetch port
        # self.assertNotEqual(pair1.cards[0], pair1.cards[1])
        # self.assertNotEqual(pair2.cards[0], pair2.cards[1])

class CardSampler(unittest.TestCase):

    def test_error_with_no_adapter():
        '''
        The port should fail to initialise with no adapter
        '''
        self.assertRaises(CardSampler(), TypeError)

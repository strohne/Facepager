from unittest import TestCase
from utilities import getDictValue

class Test_Utilities(TestCase):

    def setUp(self):
        self.fixture = {'posts': {'comments': [{'text': 'smartidea'}]}}

    def tearDown(self):
        self.fixture = None

    def test_get_dict_value(self):
        out = getDictValue(self.fixture,'posts.comments.0.text')
        self.assertEqual(out,'smartidea')

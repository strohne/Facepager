from unittest import TestCase
from utilities import getDictValue

class Test_Utilities(TestCase):

    def setUp(self):
        self.fixture = {
            'posts': {
                'comments': [
                    {'text': 'smartidea1','tags':['red']},
                    {'text': 'smartidea2','tags':['blue','green']}
                ]
            }
        }

    def tearDown(self):
        self.fixture = None

    def test_get_dict_value(self):
        out = getDictValue(self.fixture,'posts.comments.0.text')
        self.assertEqual('smartidea1',out)

        out = getDictValue(self.fixture,'posts.comments.*.tags',dump=False)
        self.assertEqual(['red','blue','green'],out)


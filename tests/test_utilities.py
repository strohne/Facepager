from unittest import TestCase
from utilities import getDictValue, extractValue

class Test_Utilities(TestCase):

    def setUp(self):
        self.fixture = {
            'posts': {
                'comments': [
                    {'text': 'smartidea1','tags':['red']},
                    {'text': 'smartidea2','tags':['blue','green']},
                    {'text': 'smartidea3', 'wild.*.card': 'party'}
                ]
            }
        }

    def tearDown(self):
        self.fixture = None

    def test_get_dict_value(self):
        out = getDictValue(self.fixture,'posts.comments.0.text')
        self.assertEqual('smartidea1',out)

        out = getDictValue(self.fixture,'posts.comments.*.tags',dump=False)
        self.assertEqual(['red','blue','green',''],out)

        out = getDictValue(self.fixture,'posts.comments.*.wild\.*\.card',dump=False)
        self.assertEqual(['','','party'],out)

    def test_extract_value(self):
        out = extractValue(self.fixture, 'posts.comments.*.wild\.*\.card', dump=False)
        self.assertEqual((None,['','','party']),out)
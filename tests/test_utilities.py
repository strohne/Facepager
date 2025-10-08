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
        # Simple text value
        out = getDictValue(self.fixture,'posts.comments.0.text')
        self.assertEqual('smartidea1',out)

        # List of text values
        out = getDictValue(self.fixture,'posts.comments.*.tags',dump=False)
        self.assertEqual(['red','blue','green',''],out)

        # Nested list of text values
        out = getDictValue(self.fixture,'posts.comments.*.wild\.*\.card',dump=False)
        self.assertEqual(['','','party'],out)

    def test_extract_value(self):
        # Simple named text value
        out = extractValue(self.fixture,'txt=posts.comments.0.text', dump=False)
        self.assertEqual(('txt','smartidea1'),out)

        # Simple named text value
        out = extractValue(self.fixture,'txt=posts.comments.0.text', dump=True)
        self.assertEqual(('txt','smartidea1'),out)

        # Nested list of text values with escaping
        out = extractValue(self.fixture, 'posts.comments.*.wild\.*\.card', dump=False)
        self.assertEqual((None,['','','party']),out)

        # Joined list of text values with escaping
        out = extractValue(self.fixture, 'posts.comments.*.wild\.*\.card', dump=True)
        self.assertEqual((None, ';;party'), out)

        # Comma separated list of values with escaping
        out = extractValue(self.fixture, 'posts.comments.*.wild\.*\.card|join:,', dump=False)
        self.assertEqual((None, ',,party'), out)

        # Comma separated list of values with escaping
        out = extractValue(self.fixture, 'posts.comments.*.wild\.*\.card|join:,', dump=True)
        self.assertEqual((None, ',,party'), out)

        # A list value
        out = extractValue(self.fixture, 'posts.comments.*.tags', dump=False)
        self.assertEqual((None, ['red', 'blue', 'green', '']), out)

        # A list value
        out = extractValue(self.fixture, 'posts.comments.*.tags', dump=True)
        self.assertEqual((None, 'red;blue;green;'), out)

        # A dict value
        out = extractValue(self.fixture, 'posts.comments.0', dump=True)
        self.assertEqual((None, '{"text": "smartidea1", "tags": ["red"]}'), out)

        # A dict value
        out = extractValue(self.fixture, 'posts.comments.0', dump=False)
        self.assertEqual((None, {"text": "smartidea1", "tags": ["red"]}), out)
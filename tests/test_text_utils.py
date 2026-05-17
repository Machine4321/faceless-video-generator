"""Tests for shadowvault.utils.text_utils."""

from shadowvault.utils.text_utils import clean_text, chunk_words, strip_json_fences


class TestCleanText:
    def test_strips_markdown(self):
        assert clean_text("**bold** [link] #heading") == "bold link heading"

    def test_collapses_whitespace(self):
        assert clean_text("hello   world\n\nnew") == "hello world new"

    def test_strips_backticks(self):
        assert clean_text("`code`") == "code"

    def test_empty_string(self):
        assert clean_text("") == ""

    def test_plain_text_unchanged(self):
        assert clean_text("normal text here") == "normal text here"


class TestChunkWords:
    def test_basic_chunking(self):
        text = "one two three four five six seven eight"
        chunks = chunk_words(text, 4)
        assert chunks == ["one two three four", "five six seven eight"]

    def test_remainder_chunk(self):
        text = "a b c d e"
        chunks = chunk_words(text, 3)
        assert chunks == ["a b c", "d e"]

    def test_empty_text(self):
        assert chunk_words("", 4) == []

    def test_single_word(self):
        assert chunk_words("hello", 4) == ["hello"]

    def test_custom_chunk_size(self):
        text = "a b c d e f"
        chunks = chunk_words(text, 2)
        assert chunks == ["a b", "c d", "e f"]


class TestStripJsonFences:
    def test_with_fences(self):
        text = '```json\n{"key": "value"}\n```'
        assert strip_json_fences(text) == '{"key": "value"}'

    def test_without_fences(self):
        text = '{"key": "value"}'
        assert strip_json_fences(text) == '{"key": "value"}'

    def test_plain_fences(self):
        text = '```\n{"key": "value"}\n```'
        assert strip_json_fences(text) == '{"key": "value"}'

    def test_whitespace_preserved_inside(self):
        text = '```json\n{\n  "key": "value"\n}\n```'
        result = strip_json_fences(text)
        assert '"key": "value"' in result

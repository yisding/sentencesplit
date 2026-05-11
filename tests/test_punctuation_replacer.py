from sentencesplit.between_punctuation import BetweenPunctuation


def test_replace_punctuation_preserves_square_brackets():
    text = "Before [Why? now.] after."

    result = BetweenPunctuation(text).replace()

    assert result == "Before [Why&ᓷ& now∯] after."


def test_replace_punctuation_preserves_parens():
    text = "Before (Go! now.) after."

    result = BetweenPunctuation(text).replace()

    assert result == "Before (Go&ᓴ& now∯) after."


def test_replace_punctuation_preserves_em_dash_delimiters():
    text = "Before --Really? yes!-- after."

    result = BetweenPunctuation(text).replace()

    assert result == "Before --Really&ᓷ& yes&ᓴ&-- after."


def test_replace_punctuation_replaces_apostrophe_inside_double_quotes():
    text = 'Before "Why? It\'s fine." after.'

    result = BetweenPunctuation(text).replace()

    assert result == 'Before "Why&ᓷ& It&⎋&s fine∯" after.'


def test_replace_punctuation_keeps_apostrophe_inside_single_quotes():
    text = "Before 'Why? It's fine.' after."

    result = BetweenPunctuation(text).replace()

    assert result == "Before 'Why&ᓷ& It's fine∯' after."

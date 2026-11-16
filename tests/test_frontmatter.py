"""Tests for markdown front-matter handling."""

import pytest

from lantoki import frontmatter


def test_given_markdown_with_front_matter_when_parsing_then_fields_and_body_are_split() -> None:
    document = frontmatter.parse("---\ndescription: X\ntags: [a, b]\n---\n# Body\n")

    assert document.front_matter == {"description": "X", "tags": ["a", "b"]}
    assert document.body == "# Body\n"


def test_given_plain_markdown_when_parsing_then_everything_is_body() -> None:
    document = frontmatter.parse("# Only body\n")

    assert document.front_matter == {}
    assert document.body == "# Only body\n"


def test_given_non_mapping_front_matter_when_parsing_then_type_error_is_raised() -> None:
    with pytest.raises(TypeError, match="mapping"):
        frontmatter.parse("---\n- a\n---\nbody\n")


def test_given_fields_and_source_when_rendering_then_output_round_trips_with_marker() -> None:
    rendered = frontmatter.render({"b": 1, "a": 'quote "x": y'}, "\n\nBody\n", "user/rules/x.md")

    document = frontmatter.parse(rendered)
    assert list(document.front_matter) == ["b", "a"]
    assert document.front_matter["a"] == 'quote "x": y'
    assert document.body == frontmatter.GENERATED_MARKER.format(source="user/rules/x.md") + "\n\nBody\n"
    assert frontmatter.is_generated(rendered)


def test_given_no_fields_and_no_source_when_rendering_then_only_body_remains() -> None:
    rendered = frontmatter.render({}, "Body\n")

    assert rendered == "Body\n"
    assert not frontmatter.is_generated(rendered)

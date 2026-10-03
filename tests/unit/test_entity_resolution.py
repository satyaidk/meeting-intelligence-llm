"""Different spellings of a name -> one person."""

import pytest

from actiongraph.enrichment.entity_resolution import (
    EntityResolver,
    KnownPerson,
    ResolutionMethod,
    names_compatible,
    normalize_person_name,
)


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("Priya", "priya"),
        ("@Priya.Sharma", "priya sharma"),
        ("priya.sharma@acme.com", "priya sharma"),
        ("Priya S.", "priya s"),
        ("Dr. Sam Lee", "sam lee"),
        ("  sam_lee ", "sam lee"),
    ],
)
def test_normalize_person_name(raw: str, expected: str) -> None:
    assert normalize_person_name(raw) == expected


@pytest.mark.parametrize(
    ("a", "b", "compatible"),
    [
        ("priya", "priya sharma", True),
        ("priya s", "priya sharma", True),
        ("priya k", "priya sharma", False),
        ("sam", "priya", False),
        ("sam lee", "sam lee", True),
    ],
)
def test_names_compatible(a: str, b: str, compatible: bool) -> None:
    assert names_compatible(a, b) is compatible


@pytest.fixture
def resolver() -> EntityResolver:
    return EntityResolver(
        [KnownPerson(key="1", display_name="Priya Sharma", aliases={"priya sharma"})]
    )


@pytest.mark.parametrize("spelling", ["Priya", "Priya S.", "@priya", "priya.sharma@acme.com"])
def test_variants_resolve_to_the_same_person(resolver: EntityResolver, spelling: str) -> None:
    result = resolver.resolve(spelling)
    assert result.person is not None
    assert result.person.key == "1"
    assert result.confidence >= 0.9


def test_matched_spellings_are_remembered_as_aliases(resolver: EntityResolver) -> None:
    resolver.resolve("Priya S.")
    assert "priya s" in resolver.people[0].aliases


def test_ambiguous_first_name_is_not_guessed() -> None:
    resolver = EntityResolver(
        [
            KnownPerson("1", "Priya Sharma", {"priya sharma"}),
            KnownPerson("2", "Priya Kumar", {"priya kumar"}),
        ]
    )
    result = resolver.resolve("Priya")
    assert result.method is ResolutionMethod.AMBIGUOUS
    assert result.person is None
    assert result.candidates == ("Priya Kumar", "Priya Sharma")
    # ...but an initial is enough to disambiguate
    assert resolver.resolve("Priya K.").person.key == "2"


def test_different_surname_is_a_different_person() -> None:
    resolver = EntityResolver([KnownPerson("1", "Priya Sharma", {"priya sharma", "priya"})])
    result = resolver.resolve("Priya Kumar")
    assert result.method is ResolutionMethod.NEW


@pytest.mark.parametrize("raw", ["Team", "we", "Everyone", "the whole team"])
def test_team_words(resolver: EntityResolver, raw: str) -> None:
    result = resolver.resolve(raw)
    assert result.is_team
    assert result.person is None


@pytest.mark.parametrize("raw", [None, "", "   "])
def test_missing_owner(resolver: EntityResolver, raw: str | None) -> None:
    assert resolver.resolve(raw).method is ResolutionMethod.NONE


def test_new_people_are_registered_and_display_name_improves() -> None:
    resolver = EntityResolver()
    first = resolver.resolve("Jordan")
    assert first.method is ResolutionMethod.NEW
    assert first.person.key == "new:1"

    second = resolver.resolve("Jordan Patel")
    assert second.person is first.person  # same meeting, same human
    assert second.person.display_name == "Jordan Patel"


def test_typos_match_by_fuzzy_spelling(resolver: EntityResolver) -> None:
    result = resolver.resolve("Pryia Sharma")
    assert result.method is ResolutionMethod.FUZZY
    assert result.person.key == "1"
    assert result.confidence < 0.9  # fuzzy matches are flagged for review

"""
Card validators - Ensure consistency between Card model and structure configuration.

These validators ensure that:
1. Each card belongs to exactly ONE valid section
2. Each card has exactly ONE valid tab within that section
3. All tags belong to the allowed set for that section-tab combination
4. The info elements count matches the expected count for that section-tab
5. Only required fields contain values, hidden fields are null
6. User has permission to add articles to this section-tab
"""

from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _
from section.structure import (
    validate_card_consistency,
    is_section_valid,
    is_tab_valid,
    get_tags_for_tab,
    get_expected_info_elements_count,
    get_can_add_article_roles,
    get_required_fields,
    UserRole,
)


def validate_card_section_and_tab(section: str, tab: str) -> None:
    """
    Validate that section and tab are valid and consistent.

    Args:
        section: The card's section
        tab: The card's tab

    Raises:
        ValidationError: If section or tab are invalid
    """
    if not section:
        raise ValidationError(_("Section is required"))

    if not tab:
        raise ValidationError(_("Tab is required"))

    if not is_section_valid(section):
        raise ValidationError(
            _(f"Invalid section: {section}")
        )

    if not is_tab_valid(section, tab):
        raise ValidationError(
            _(f"Invalid tab '{tab}' for section '{section}'")
        )


def validate_card_tags(section: str, tab: str, tags: list) -> None:
    """
    Validate that all tags belong to the allowed set for the section-tab.

    Args:
        section: The card's section
        tab: The card's tab
        tags: The card's tags

    Raises:
        ValidationError: If any tag is invalid
    """
    if not section or not tab:
        return  # Skip validation if section/tab are invalid

    allowed_tags = get_tags_for_tab(section, tab)

    for tag in tags:
        if tag not in allowed_tags:
            raise ValidationError(
                _(
                    f"Invalid tag '{tag}' for section '{section}', tab '{tab}'. "
                    f"Allowed tags: {', '.join(allowed_tags)}"
                )
            )


def validate_card_info_elements_count(section: str, tab: str, info_elements_count: int) -> None:
    """
    Validate that the info elements count matches the expected count.

    Args:
        section: The card's section
        tab: The card's tab
        info_elements_count: The number of info elements

    Raises:
        ValidationError: If the count doesn't match
    """
    if not section or not tab:
        return  # Skip validation if section/tab are invalid

    expected_count = get_expected_info_elements_count(section, tab)
    if info_elements_count != expected_count:
        raise ValidationError(
            _(
                f"Invalid info elements count for section '{section}', tab '{tab}'. "
                f"Expected {expected_count}, got {info_elements_count}"
            )
        )


def validate_can_user_add_article(section: str, tab: str, user_role: UserRole) -> None:
    """
    Validate that the user has permission to add articles to this section-tab.

    Args:
        section: The card's section
        tab: The card's tab
        user_role: The user's role

    Raises:
        ValidationError: If user doesn't have permission
    """
    if not section or not tab:
        return  # Skip validation if section/tab are invalid

    allowed_roles = get_can_add_article_roles(section, tab)
    if user_role not in allowed_roles:
        raise ValidationError(
            _(
                f"User with role '{user_role}' cannot add articles to section '{section}', tab '{tab}'. "
                f"Allowed roles: {', '.join(allowed_roles)}"
            )
        )


def validate_card_consistency_all(
    section: str,
    tab: str,
    tags: list,
    info_elements_count: int,
    user_role: UserRole = 'user',
) -> None:
    """
    Validate all card consistency rules at once.

    Args:
        section: The card's section
        tab: The card's tab
        tags: The card's tags
        info_elements_count: The number of info elements
        user_role: The user's role (default 'user')

    Raises:
        ValidationError: If any validation fails
    """
    is_valid, errors = validate_card_consistency(section, tab, tags, info_elements_count)

    if not is_valid:
        raise ValidationError(
            _("Card consistency validation failed:") + "\n" + "\n".join(errors)
        )

    # Additional check: user permission
    try:
        validate_can_user_add_article(section, tab, user_role)
    except ValidationError:
        raise

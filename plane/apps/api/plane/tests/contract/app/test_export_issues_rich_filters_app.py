# Copyright (c) 2023-present Plane Software, Inc. and contributors
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

"""Contract tests for ExportIssuesEndpoint's rich_filters extension.

Covers the spec (okto-plane-handoff-demo, board d72390b0-43d9-4448-883b-e5937f8e4454,
spec e4720b70-f539-44fa-8f2f-b4cf140d9f3a) test scenarios:
  ts_09958d47 — unrecognized filter key rejects the request (400, no row created)
  ts_28b5c180 — legacy request without rich_filters is unaffected
And, at the unit level below, the queryset-narrowing behavior underlying
  ts_f858606d — export respects the active filter and sort.
"""

from unittest.mock import patch

import pytest
from rest_framework import status
from rest_framework.exceptions import ValidationError as DRFValidationError

from plane.bgtasks.export_task import _apply_rich_filters
from plane.db.models import ExporterHistory, Issue, Project, ProjectMember

EXPORT_URL = "/api/workspaces/{slug}/export-issues/"


@pytest.fixture
def project(db, workspace, create_user):
    project = Project.objects.create(
        name="Export Project", identifier="EXP", workspace=workspace, created_by=create_user
    )
    ProjectMember.objects.create(project=project, member=create_user, workspace=workspace, role=20)
    return project


@pytest.mark.contract
class TestExportIssuesRichFiltersEndpoint:
    """ts_09958d47 and ts_28b5c180: request-level (endpoint) behavior."""

    @pytest.mark.django_db
    @patch("plane.app.views.exporter.base.issue_export_task.delay")
    def test_unrecognized_filter_key_rejects_with_400(self, mock_delay, session_client, workspace, project):
        url = EXPORT_URL.format(slug=workspace.slug)
        response = session_client.post(
            url,
            {
                "provider": "csv",
                "project": [str(project.id)],
                "rich_filters": {"filters": {"not_a_real_filter__in": "x"}},
            },
            format="json",
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST, (
            f"Got {response.status_code}: {getattr(response, 'data', None)!r}"
        )
        assert response.data.get("error") == "invalid_filter_key"
        # No ExporterHistory row created for this rejected request.
        assert not ExporterHistory.objects.filter(workspace=workspace, type="issue_exports").exists()
        # And the Celery task was never queued.
        mock_delay.assert_not_called()

    @pytest.mark.django_db
    @patch("plane.app.views.exporter.base.issue_export_task.delay")
    def test_legacy_request_without_rich_filters_is_unaffected(self, mock_delay, session_client, workspace, project):
        url = EXPORT_URL.format(slug=workspace.slug)
        response = session_client.post(
            url, {"provider": "csv", "project": [str(project.id)]}, format="json"
        )

        assert response.status_code == status.HTTP_200_OK, (
            f"Got {response.status_code}: {getattr(response, 'data', None)!r}"
        )
        assert ExporterHistory.objects.filter(workspace=workspace, type="issue_exports").count() == 1
        exporter = ExporterHistory.objects.get(workspace=workspace, type="issue_exports")
        assert exporter.rich_filters is None
        mock_delay.assert_called_once()
        assert mock_delay.call_args.kwargs.get("rich_filters") is None

    @pytest.mark.django_db
    @patch("plane.app.views.exporter.base.issue_export_task.delay")
    def test_valid_rich_filters_are_persisted_verbatim_and_queued(self, mock_delay, session_client, workspace, project):
        url = EXPORT_URL.format(slug=workspace.slug)
        payload = {
            "provider": "csv",
            "project": [str(project.id)],
            "rich_filters": {"filters": {"priority__in": "urgent"}, "order_by": "-created_at"},
        }
        response = session_client.post(url, payload, format="json")

        assert response.status_code == status.HTTP_200_OK, (
            f"Got {response.status_code}: {getattr(response, 'data', None)!r}"
        )
        exporter = ExporterHistory.objects.get(workspace=workspace, type="issue_exports")
        assert exporter.rich_filters == payload["rich_filters"]
        mock_delay.assert_called_once()
        assert mock_delay.call_args.kwargs.get("rich_filters") == payload["rich_filters"]


@pytest.mark.unit
class TestApplyRichFilters:
    """ts_f858606d: the queryset-narrowing behavior _apply_rich_filters implements."""

    @pytest.mark.django_db
    def test_narrows_to_matching_priority_only(self, db, workspace, project, create_user):
        urgent = Issue.objects.create(
            name="Urgent one", project=project, workspace=workspace, priority="urgent", created_by=create_user
        )
        Issue.objects.create(
            name="Low one", project=project, workspace=workspace, priority="low", created_by=create_user
        )

        base_qs = Issue.objects.filter(workspace=workspace, project=project)
        filtered = _apply_rich_filters(base_qs, {"filters": {"and": [{"priority__in": "urgent"}]}})

        ids = set(filtered.values_list("id", flat=True))
        assert ids == {urgent.id}

    @pytest.mark.django_db
    def test_no_rich_filters_returns_queryset_unchanged(self, db, workspace, project, create_user):
        Issue.objects.create(name="A", project=project, workspace=workspace, created_by=create_user)
        Issue.objects.create(name="B", project=project, workspace=workspace, created_by=create_user)

        base_qs = Issue.objects.filter(workspace=workspace, project=project)
        result = _apply_rich_filters(base_qs, None)

        assert result.count() == base_qs.count() == 2

    @pytest.mark.django_db
    def test_unrecognized_key_raises_validation_error(self, db, workspace, project, create_user):
        base_qs = Issue.objects.filter(workspace=workspace, project=project)
        with pytest.raises(DRFValidationError):
            _apply_rich_filters(base_qs, {"filters": {"not_a_real_filter__in": "x"}})

    @pytest.mark.django_db
    def test_order_by_returns_a_queryset_not_a_tuple(self, db, workspace, project, create_user):
        """Regression: order_issue_queryset returns (queryset, order_by_param),
        not just the queryset. A caller that assigns its return value directly
        as the queryset silently turns the export's iterable into a 2-tuple
        whose first element is itself a queryset — caught in a real end-to-end
        run against the live stack (Celery worker), not by mocks: DRF's
        serializer iterated the tuple's queryset element as if it were a
        single Issue and crashed with 'SoftDeletionQuerySet has no attribute
        parent'. This asserts the real, iterable-of-Issue shape."""
        Issue.objects.create(
            name="Newer", project=project, workspace=workspace, priority="urgent", created_by=create_user
        )
        Issue.objects.create(
            name="Older", project=project, workspace=workspace, priority="urgent", created_by=create_user
        )

        base_qs = Issue.objects.filter(workspace=workspace, project=project)
        result = _apply_rich_filters(base_qs, {"filters": {}, "order_by": "-created_at"})

        # Must be directly iterable into Issue instances (not a tuple whose
        # first element is the queryset) — mirrors what
        # IssueExportSerializer(..., many=True) actually does.
        items = list(result)
        assert len(items) == 2
        assert all(isinstance(item, Issue) for item in items)
        assert all(hasattr(item, "parent") and not hasattr(item.parent, "count") for item in items)

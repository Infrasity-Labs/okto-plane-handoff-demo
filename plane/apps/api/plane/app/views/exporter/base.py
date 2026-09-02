# Copyright (c) 2023-present Plane Software, Inc. and contributors
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

# Third Party imports
from rest_framework import status
from rest_framework.response import Response

from rest_framework.exceptions import ValidationError as DRFValidationError

from plane.app.permissions import allow_permission, ROLE
from plane.app.serializers import ExporterHistorySerializer
from plane.bgtasks.export_task import issue_export_task
from plane.db.models import ExporterHistory, Project, Workspace
from plane.utils.filters import ComplexFilterBackend, IssueFilterSet

# Module imports
from .. import BaseAPIView


class _IssueFilterView:
    """Minimal view-shaped shim: ComplexFilterBackend only reads
    `filterset_class` off the `view` it's handed, and this endpoint isn't
    itself the Issues List view. See the matching shim in bgtasks/export_task.py."""

    filterset_class = IssueFilterSet


class ExportIssuesEndpoint(BaseAPIView):
    model = ExporterHistory
    serializer_class = ExporterHistorySerializer

    @allow_permission(allowed_roles=[ROLE.ADMIN, ROLE.MEMBER], level="WORKSPACE")
    def post(self, request, slug):
        # Get the workspace
        workspace = Workspace.objects.get(slug=slug)

        provider = request.data.get("provider", False)
        multiple = request.data.get("multiple", False)
        project_ids = request.data.get("project", [])
        rich_filters = request.data.get("rich_filters")

        if provider in ["csv", "xlsx", "json"]:
            # rich_filters lets a caller (e.g. the Issues List view's Export
            # action) scope the export to the view's active filter/sort
            # state. `filters` is the SAME JSON filter-tree shape the Issues
            # List view's own richFilters store already produces and that
            # ComplexFilterBackend already consumes for the list endpoint
            # (e.g. {"and": [{"priority__in": "urgent,high"}]}, or a single
            # bare leaf) — validated up front against IssueFilterSet's
            # declared fields via the same backend. An unrecognized key
            # fails closed with 400 before any ExporterHistory row is
            # created, per BR "unknown filter keys reject the request rather
            # than degrading silently".
            if rich_filters is not None:
                if not isinstance(rich_filters, dict):
                    return Response(
                        {
                            "error": "invalid_filter_key",
                            "detail": "rich_filters must be an object.",
                        },
                        status=status.HTTP_400_BAD_REQUEST,
                    )
                filter_tree = rich_filters.get("filters") or {}
                backend = ComplexFilterBackend()
                try:
                    backend._validate_structure(
                        filter_tree, max_depth=backend._get_max_depth(_IssueFilterView()), current_depth=1
                    )
                    backend._validate_fields(filter_tree, _IssueFilterView())
                except DRFValidationError as e:
                    return Response(
                        {"error": "invalid_filter_key", "detail": e.detail},
                        status=status.HTTP_400_BAD_REQUEST,
                    )
                rich_project_id = rich_filters.get("project_id")
                if rich_project_id and not project_ids:
                    project_ids = [str(rich_project_id)]

            if not project_ids:
                project_ids = Project.objects.filter(
                    workspace__slug=slug,
                    project_projectmember__member=request.user,
                    project_projectmember__is_active=True,
                    archived_at__isnull=True,
                ).values_list("id", flat=True)
                project_ids = [str(project_id) for project_id in project_ids]

            exporter = ExporterHistory.objects.create(
                workspace=workspace,
                project=project_ids,
                initiated_by=request.user,
                provider=provider,
                type="issue_exports",
                # Persisted verbatim (not the converted form) for audit/replay.
                rich_filters=rich_filters,
            )

            issue_export_task.delay(
                provider=exporter.provider,
                workspace_id=workspace.id,
                project_ids=project_ids,
                token_id=exporter.token,
                multiple=multiple,
                slug=slug,
                rich_filters=rich_filters,
            )
            return Response(
                {"message": "Once the export is ready you will be able to download it"},
                status=status.HTTP_200_OK,
            )
        else:
            return Response(
                {"error": f"Provider '{provider}' not found."},
                status=status.HTTP_400_BAD_REQUEST,
            )

    @allow_permission(allowed_roles=[ROLE.ADMIN, ROLE.MEMBER], level="WORKSPACE")
    def get(self, request, slug):
        exporter_history = ExporterHistory.objects.filter(workspace__slug=slug, type="issue_exports").select_related(
            "workspace", "initiated_by"
        )

        if request.GET.get("per_page", False) and request.GET.get("cursor", False):
            return self.paginate(
                order_by=request.GET.get("order_by", "-created_at"),
                request=request,
                queryset=exporter_history,
                on_results=lambda exporter_history: ExporterHistorySerializer(exporter_history, many=True).data,
            )
        else:
            return Response(
                {"error": "per_page and cursor are required"},
                status=status.HTTP_400_BAD_REQUEST,
            )

/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { useCallback, useEffect, useRef, useState } from "react";
import { observer } from "mobx-react";
import { Download, Loader2 } from "lucide-react";
// plane imports
import { useTranslation } from "@plane/i18n";
import { Button } from "@plane/propel/button";
import { TOAST_TYPE, setToast } from "@plane/propel/toast";
import { EIssuesStoreType } from "@plane/types";
// hooks
import { useIssues } from "@/hooks/store/use-issues";
// services
import { IntegrationService } from "@/services/integrations";
import { ProjectExportService } from "@/services/project/project-export.service";

const integrationService = new IntegrationService();
const projectExportService = new ProjectExportService();

const POLL_INTERVAL_MS = 3000;

type Props = {
  workspaceSlug: string;
  projectId: string;
  canExport: boolean | undefined;
};

/**
 * Export CSV action for the Issues List toolbar. Filter-aware: sends the
 * view's current richFilters (same JSON filter-tree shape the Issues List
 * view already maintains — see packages/shared-state's work-item-filters
 * adapter) so the export contains exactly what's on screen. Reuses the
 * existing async ExportIssuesEndpoint/issue_export_task pipeline: queues a
 * job, then polls ExporterHistory (same 3000ms interval PrevExports already
 * uses) for completed/failed, matching the app's one established
 * async-export UX pattern rather than inventing a new one.
 */
export const ExportCsvAction = observer(function ExportCsvAction(props: Props) {
  const { workspaceSlug, projectId, canExport } = props;
  const { t } = useTranslation();
  const {
    issuesFilter: { issueFilters },
  } = useIssues(EIssuesStoreType.PROJECT);

  const [state, setState] = useState<"idle" | "queued" | "completed" | "failed">("idle");
  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const submittedAtRef = useRef<number>(0);

  const stopPolling = useCallback(() => {
    if (pollRef.current) {
      clearInterval(pollRef.current);
      pollRef.current = null;
    }
  }, []);

  useEffect(() => () => stopPolling(), [stopPolling]);

  const pollForResult = useCallback(() => {
    stopPolling();
    pollRef.current = setInterval(async () => {
      try {
        const res = await integrationService.getExportsServicesList(workspaceSlug, "", 1);
        const latest = res?.results?.[0];
        if (!latest) return;
        // Our own submission is the newest csv row created after we clicked.
        const latestCreatedAt = new Date(latest.created_at).getTime();
        if (latest.provider !== "csv" || latestCreatedAt < submittedAtRef.current) return;

        if (latest.status === "completed") {
          stopPolling();
          setState("completed");
          setToast({
            type: TOAST_TYPE.SUCCESS,
            title: t("issue.export.ready.title", { defaultValue: "Export ready" }),
            message: t("issue.export.ready.message", {
              defaultValue: "Your CSV export is ready to download.",
            }),
          });
          if (latest.url && typeof window !== "undefined") {
            window.open(latest.url, "_blank", "noopener,noreferrer");
          }
        } else if (latest.status === "failed") {
          stopPolling();
          setState("failed");
          setToast({
            type: TOAST_TYPE.ERROR,
            title: t("error"),
            message: t("issue.export.failed.message", {
              defaultValue: "The export failed. Please try again.",
            }),
          });
        }
      } catch (_error) {
        // Transient poll failure — leave the interval running, matching
        // PrevExports' own tolerance of individual refresh failures.
      }
    }, POLL_INTERVAL_MS);
  }, [workspaceSlug, stopPolling, t]);

  const handleExport = useCallback(async () => {
    if (!workspaceSlug || !projectId) return;
    setState("queued");
    submittedAtRef.current = Date.now();
    try {
      await projectExportService.csvExport(workspaceSlug, {
        provider: "csv",
        project: [projectId],
        multiple: false,
        // Same richFilters the view is currently rendering — exports
        // exactly what's on screen. `filters`/`order_by` land verbatim on
        // ExporterHistory.rich_filters and are applied server-side via the
        // same ComplexFilterBackend the Issues List endpoint already uses.
        rich_filters: {
          filters: issueFilters?.richFilters ?? {},
          order_by: issueFilters?.displayFilters?.order_by,
        } as never,
      });
      setToast({
        type: TOAST_TYPE.SUCCESS,
        title: t("workspace_settings.settings.exports.modal.toasts.success.title"),
        message: t("workspace_settings.settings.exports.modal.toasts.success.message", { entity: "CSV" }),
      });
      pollForResult();
    } catch (_error) {
      setState("failed");
      setToast({
        type: TOAST_TYPE.ERROR,
        title: t("error"),
        message: t("workspace_settings.settings.exports.modal.toasts.error.message"),
      });
    }
  }, [workspaceSlug, projectId, issueFilters, pollForResult, t]);

  if (!canExport) return null;

  const isBusy = state === "queued";

  return (
    <Button variant="secondary" size="lg" onClick={handleExport} disabled={isBusy}>
      {isBusy ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <Download className="h-3.5 w-3.5" />}
      <span className="hidden sm:block">{t("issue.export.action", { defaultValue: "Export CSV" })}</span>
    </Button>
  );
});

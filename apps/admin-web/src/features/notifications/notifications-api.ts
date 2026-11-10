import type { components } from "@kabisa/shared";
import { apiClient } from "@/lib/api-client";

export type NotificationFeed = components["schemas"]["AdminNotificationFeed"];
export type StaffNotification = components["schemas"]["AdminNotificationRead"];
export type NotificationCursor = { before_at: string; before_id: string } | undefined;

export async function getNotifications(
  cursor?: NotificationCursor,
): Promise<NotificationFeed> {
  const { data } = await apiClient.get<NotificationFeed>("/notifications", {
    params: cursor,
  });
  return data;
}

export async function markNotificationsOpened(through: string) {
  const { data } = await apiClient.post<components["schemas"]["AdminNotificationOpened"]>(
    "/notifications/opened",
    { through },
  );
  return data;
}

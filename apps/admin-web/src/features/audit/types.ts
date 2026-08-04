export type AuditActor = {
  id: string;
  name: string;
  email: string;
};

export type AuditLog = {
  id: string;
  actor_id: string | null;
  actor: AuditActor | null;
  action: string;
  entity_type: string;
  entity_id: string | null;
  changes: Record<string, unknown> | null;
  ip_address: string | null;
  created_at: string;
};

export type AuditLogList = {
  items: AuditLog[];
  total: number;
  page: number;
  page_size: number;
};

export type AuditOption = {
  value: string;
  label: string;
};

export type AuditOptions = {
  actors: AuditActor[];
  actions: AuditOption[];
  entity_types: AuditOption[];
};

export type AuditFilters = {
  page?: number;
  page_size?: number;
  actor_id?: string;
  action?: string;
  entity_type?: string;
  date_from?: string;
  date_to?: string;
  search?: string;
};

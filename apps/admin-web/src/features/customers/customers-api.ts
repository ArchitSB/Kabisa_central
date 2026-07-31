import type { ListResponse } from "@/features/catalog/types";
import type {
  Customer,
  CustomerAddress,
  CustomerAddressPayload,
  CustomerDetail,
  CustomerDocument,
  CustomerFeedback,
  CustomerPayload,
  DocumentStatus,
  DocumentType,
} from "@/features/customers/types";
import { apiClient } from "@/lib/api-client";

const listParams = { page: 1, page_size: 100 };

export type CustomerFilters = {
  search?: string;
  business_type?: string;
  status?: string;
  price_tier_id?: string;
  payment_terms?: string;
  region?: string;
};

export async function listCustomers(filters: CustomerFilters = {}) {
  const response = await apiClient.get<ListResponse<Customer>>("/customers", {
    params: { ...listParams, sort: "business_name:asc", ...filters },
  });
  return response.data;
}

export async function getCustomer(id: string) {
  const response = await apiClient.get<CustomerDetail>(`/customers/${id}`);
  return response.data;
}

export async function saveCustomer(payload: CustomerPayload, id?: string) {
  const response = id
    ? await apiClient.patch<CustomerDetail>(`/customers/${id}`, payload)
    : await apiClient.post<CustomerDetail>("/customers", payload);
  return response.data;
}

export async function deleteCustomer(id: string) {
  await apiClient.delete(`/customers/${id}`);
}

export async function submitCustomer(id: string) {
  const response = await apiClient.post<CustomerDetail>(
    `/customers/${id}/submit-for-review`,
  );
  return response.data;
}

export async function verifyCustomer(id: string, justification_note: string | null) {
  const response = await apiClient.post<CustomerDetail>(`/customers/${id}/verify`, {
    justification_note,
  });
  return response.data;
}

export async function rejectCustomer(id: string, rejection_reason: string) {
  const response = await apiClient.post<CustomerDetail>(`/customers/${id}/reject`, {
    rejection_reason,
  });
  return response.data;
}

export async function suspendCustomer(id: string, reason: string) {
  const response = await apiClient.post<CustomerDetail>(`/customers/${id}/suspend`, {
    reason,
  });
  return response.data;
}

export async function reinstateCustomer(id: string, reason: string) {
  const response = await apiClient.post<CustomerDetail>(`/customers/${id}/reinstate`, {
    reason,
  });
  return response.data;
}

export async function uploadCustomerDocument(
  customerId: string,
  documentType: DocumentType,
  file: File,
) {
  const body = new FormData();
  body.append("doc_type", documentType);
  body.append("file", file);
  const response = await apiClient.post<CustomerDocument>(
    `/customers/${customerId}/documents`,
    body,
    { headers: { "Content-Type": "multipart/form-data" }, timeout: 30_000 },
  );
  return response.data;
}

export async function reviewCustomerDocument(
  id: string,
  status: DocumentStatus,
  notes: string | null,
) {
  const response = await apiClient.patch<CustomerDocument>(`/customer-documents/${id}`, {
    status,
    notes,
  });
  return response.data;
}

export async function deleteCustomerDocument(id: string) {
  await apiClient.delete(`/customer-documents/${id}`);
}

export async function downloadCustomerDocument(document: CustomerDocument) {
  const response = await apiClient.get<Blob>(
    `/customer-documents/${document.id}/download`,
    { responseType: "blob" },
  );
  const url = URL.createObjectURL(response.data);
  const anchor = window.document.createElement("a");
  anchor.href = url;
  anchor.download = document.original_filename;
  window.document.body.appendChild(anchor);
  anchor.click();
  anchor.remove();
  URL.revokeObjectURL(url);
}

export async function saveCustomerAddress(
  customerId: string,
  payload: CustomerAddressPayload,
  addressId?: string,
) {
  const response = addressId
    ? await apiClient.patch<CustomerAddress>(
        `/customers/${customerId}/addresses/${addressId}`,
        payload,
      )
    : await apiClient.post<CustomerAddress>(`/customers/${customerId}/addresses`, payload);
  return response.data;
}

export async function setDefaultAddress(customerId: string, addressId: string) {
  const response = await apiClient.post<CustomerAddress>(
    `/customers/${customerId}/addresses/${addressId}/set-default`,
  );
  return response.data;
}

export async function deleteCustomerAddress(customerId: string, addressId: string) {
  await apiClient.delete(`/customers/${customerId}/addresses/${addressId}`);
}

export async function listFeedback(
  filters: { search?: string; is_handled?: boolean } = {},
) {
  const response = await apiClient.get<ListResponse<CustomerFeedback>>(
    "/customer-feedback",
    { params: { ...listParams, ...filters } },
  );
  return response.data;
}

export async function createFeedback(
  customerId: string,
  payload: { subject: string | null; message: string },
) {
  const response = await apiClient.post<CustomerFeedback>(
    `/customers/${customerId}/feedback`,
    payload,
  );
  return response.data;
}

export async function setFeedbackHandled(id: string, is_handled: boolean) {
  const response = await apiClient.patch<CustomerFeedback>(`/customer-feedback/${id}`, {
    is_handled,
  });
  return response.data;
}

import axios from "axios";

export const apiBaseUrl = import.meta.env.VITE_API_URL ?? "http://localhost:8000/api/v1";

export const authClient = axios.create({
  baseURL: apiBaseUrl,
  headers: {
    "Content-Type": "application/json",
  },
  timeout: 10_000,
});

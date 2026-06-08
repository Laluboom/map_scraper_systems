import axios from "axios";

// PH-021: Change BASE_URL to your production backend URL when deploying
const BASE_URL =
  process.env.REACT_APP_API_URL || "http://localhost:8000";

const client = axios.create({
  baseURL: BASE_URL,
  headers: { "Content-Type": "application/json" },
});

export const getTradersApi = (params) => client.get("/traders/", { params });
export const approveTraderApi = (id) => client.patch(`/traders/${id}/approve`);
export const rejectTraderApi = (id) => client.patch(`/traders/${id}/reject`);

export const startCampaignApi = (payload) => client.post("/campaigns/start", payload);
export const getCampaignApi = (id) => client.get(`/campaigns/${id}/status`);
export const listCampaignsApi = () => client.get("/campaigns/");

export const getLogsApi = (params) => client.get("/logs/", { params });

export const startScrapeApi = (source, regions) =>
  client.post("/scrape/start", { source, regions });

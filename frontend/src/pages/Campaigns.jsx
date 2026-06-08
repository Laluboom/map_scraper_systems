import React, { useEffect, useState } from "react";
import { Typography, TextField, Button, Stack, Chip } from "@mui/material";
import CampaignMonitor from "../components/CampaignMonitor";
import { startCampaignApi, listCampaignsApi } from "../api/client";

export default function Campaigns() {
  const [campaigns, setCampaigns] = useState([]);
  const [name, setName] = useState("");
  const [regions, setRegions] = useState("");

  const load = () => listCampaignsApi().then((r) => setCampaigns(r.data)).catch(() => {});
  useEffect(() => { load(); }, []);

  const handleStart = () => {
    const regionList = regions.split(",").map((r) => r.trim()).filter(Boolean);
    startCampaignApi({ name, target_regions: regionList }).then(load);
  };

  return (
    <>
      <Typography variant="h5" gutterBottom>Campaigns</Typography>
      <Stack direction="row" spacing={2} alignItems="center" sx={{ mb: 3 }}>
        <TextField size="small" label="Campaign name" value={name} onChange={(e) => setName(e.target.value)} />
        <TextField size="small" label="Regions (comma-separated)" value={regions} onChange={(e) => setRegions(e.target.value)} sx={{ width: 300 }} />
        <Button variant="contained" onClick={handleStart} disabled={!name}>Start Campaign</Button>
      </Stack>
      <CampaignMonitor campaigns={campaigns} onRefresh={load} />
    </>
  );
}

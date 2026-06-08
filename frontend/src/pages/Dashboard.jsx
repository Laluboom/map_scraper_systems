import React, { useEffect, useState } from "react";
import { Grid, Card, CardContent, Typography } from "@mui/material";
import { listCampaignsApi } from "../api/client";

export default function Dashboard() {
  const [campaigns, setCampaigns] = useState([]);

  useEffect(() => {
    listCampaignsApi().then((r) => setCampaigns(r.data)).catch(() => {});
  }, []);

  const latest = campaigns[0];

  const stats = [
    { label: "Total Campaigns", value: campaigns.length },
    { label: "Latest Status", value: latest?.status ?? "—" },
    { label: "Sent (Latest)", value: latest?.sent_count ?? "—" },
    { label: "Bounced (Latest)", value: latest?.bounced_count ?? "—" },
  ];

  return (
    <>
      <Typography variant="h5" gutterBottom>Dashboard</Typography>
      <Grid container spacing={2}>
        {stats.map((s) => (
          <Grid item xs={12} sm={6} md={3} key={s.label}>
            <Card>
              <CardContent>
                <Typography variant="subtitle2" color="text.secondary">{s.label}</Typography>
                <Typography variant="h4">{s.value}</Typography>
              </CardContent>
            </Card>
          </Grid>
        ))}
      </Grid>
    </>
  );
}

import React, { useState } from "react";
import { Typography, TextField, Button, Alert, Stack, Divider } from "@mui/material";
import RegionUpload from "../components/RegionUpload";
import { startScrapeApi } from "../api/client";

const SOURCES = ["isri", "bir", "cari", "yellowpages", "kompass", "europages", "thomasnet", "scrapmonster", "recycling_intl", "epa"];

export default function Settings() {
  const [source, setSource] = useState("isri");
  const [message, setMessage] = useState("");

  const handleScrape = () => {
    startScrapeApi(source, []).then((r) => {
      setMessage(`Scrape queued: task ${r.data.task_id}`);
    }).catch(() => setMessage("Failed to start scrape."));
  };

  return (
    <>
      <Typography variant="h5" gutterBottom>Settings</Typography>

      <Typography variant="h6" sx={{ mt: 2 }}>Trigger Scraper</Typography>
      <Stack direction="row" spacing={2} alignItems="center" sx={{ mt: 1 }}>
        <TextField select size="small" label="Source" value={source} onChange={(e) => setSource(e.target.value)} SelectProps={{ native: true }}>
          {SOURCES.map((s) => <option key={s} value={s}>{s}</option>)}
        </TextField>
        <Button variant="outlined" onClick={handleScrape}>Start Scrape</Button>
      </Stack>
      {message && <Alert severity="info" sx={{ mt: 1 }}>{message}</Alert>}

      <Divider sx={{ my: 3 }} />

      <Typography variant="h6">Upload Regions (CSV)</Typography>
      <RegionUpload />

      <Divider sx={{ my: 3 }} />

      <Typography variant="body2" color="text.secondary">
        API keys and throttle settings are configured via the <code>.env</code> file on the server.
        See <code>PLACEHOLDERS.md</code> for the full list of values to fill in.
      </Typography>
    </>
  );
}

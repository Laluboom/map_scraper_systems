import React, { useState } from "react";
import { Button, Alert, Typography } from "@mui/material";

export default function RegionUpload() {
  const [regions, setRegions] = useState([]);
  const [message, setMessage] = useState("");

  const handleFile = (e) => {
    const file = e.target.files[0];
    if (!file) return;
    const reader = new FileReader();
    reader.onload = (evt) => {
      const lines = evt.target.result.split("\n").map((l) => l.trim()).filter(Boolean);
      setRegions(lines);
      setMessage(`Loaded ${lines.length} regions. Use these when starting a campaign.`);
    };
    reader.readAsText(file);
  };

  return (
    <>
      <Typography variant="body2" sx={{ mb: 1 }}>
        Upload a CSV with one region per line (city, state, or country).
      </Typography>
      <Button variant="outlined" component="label">
        Choose CSV
        <input type="file" accept=".csv,.txt" hidden onChange={handleFile} />
      </Button>
      {message && <Alert severity="success" sx={{ mt: 1 }}>{message}</Alert>}
      {regions.length > 0 && (
        <Typography variant="caption" display="block" sx={{ mt: 1 }}>
          Preview: {regions.slice(0, 5).join(", ")}{regions.length > 5 ? ` … +${regions.length - 5} more` : ""}
        </Typography>
      )}
    </>
  );
}

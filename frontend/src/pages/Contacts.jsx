import React, { useEffect, useState } from "react";
import { Typography, FormControlLabel, Switch, Button, CircularProgress } from "@mui/material";
import TraderTable from "../components/TraderTable";
import { getTradersApi, approveTraderApi, rejectTraderApi } from "../api/client";

export default function Contacts() {
  const [traders, setTraders] = useState([]);
  const [priorityOnly, setPriorityOnly] = useState(false);
  const [loading, setLoading] = useState(false);

  const load = () => {
    setLoading(true);
    getTradersApi({ priority_only: priorityOnly, limit: 200 })
      .then((r) => setTraders(r.data))
      .finally(() => setLoading(false));
  };

  useEffect(load, [priorityOnly]);

  const handleApprove = (id) => approveTraderApi(id).then(load);
  const handleReject = (id) => rejectTraderApi(id).then(load);

  return (
    <>
      <Typography variant="h5" gutterBottom>Contacts</Typography>
      <FormControlLabel
        control={<Switch checked={priorityOnly} onChange={(e) => setPriorityOnly(e.target.checked)} />}
        label="Priority traders only"
      />
      {loading ? <CircularProgress sx={{ mt: 2 }} /> : (
        <TraderTable traders={traders} onApprove={handleApprove} onReject={handleReject} />
      )}
    </>
  );
}

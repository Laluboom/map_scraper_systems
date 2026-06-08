import React, { useEffect, useState } from "react";
import { Typography, Table, TableHead, TableRow, TableCell, TableBody, Chip, CircularProgress } from "@mui/material";
import { getLogsApi } from "../api/client";

const STATUS_COLOR = { sent: "success", bounced: "error", replied: "info", pending: "default" };

export default function Logs() {
  const [logs, setLogs] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    getLogsApi({ limit: 200 }).then((r) => setLogs(r.data)).finally(() => setLoading(false));
  }, []);

  return (
    <>
      <Typography variant="h5" gutterBottom>Email Logs</Typography>
      {loading ? <CircularProgress /> : (
        <Table size="small">
          <TableHead>
            <TableRow>
              <TableCell>Trader ID</TableCell>
              <TableCell>Status</TableCell>
              <TableCell>SendGrid ID</TableCell>
              <TableCell>Error</TableCell>
              <TableCell>Sent At</TableCell>
            </TableRow>
          </TableHead>
          <TableBody>
            {logs.map((log) => (
              <TableRow key={log.id}>
                <TableCell>{log.trader_id.slice(0, 8)}…</TableCell>
                <TableCell><Chip label={log.status} color={STATUS_COLOR[log.status] || "default"} size="small" /></TableCell>
                <TableCell>{log.sendgrid_message_id || "—"}</TableCell>
                <TableCell>{log.error_message || "—"}</TableCell>
                <TableCell>{new Date(log.created_at).toLocaleString()}</TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      )}
    </>
  );
}

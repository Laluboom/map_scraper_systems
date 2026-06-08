import React from "react";
import { Table, TableHead, TableRow, TableCell, TableBody, Chip, Button } from "@mui/material";

const STATUS_COLOR = { running: "warning", done: "success", created: "default", paused: "info" };

export default function CampaignMonitor({ campaigns, onRefresh }) {
  return (
    <>
      <Button size="small" onClick={onRefresh} sx={{ mb: 1 }}>Refresh</Button>
      <Table size="small">
        <TableHead>
          <TableRow>
            <TableCell>Name</TableCell>
            <TableCell>Status</TableCell>
            <TableCell>Total</TableCell>
            <TableCell>Sent</TableCell>
            <TableCell>Bounced</TableCell>
            <TableCell>Replied</TableCell>
            <TableCell>Created</TableCell>
          </TableRow>
        </TableHead>
        <TableBody>
          {campaigns.map((c) => (
            <TableRow key={c.id}>
              <TableCell>{c.name}</TableCell>
              <TableCell><Chip label={c.status} color={STATUS_COLOR[c.status] || "default"} size="small" /></TableCell>
              <TableCell>{c.total_traders}</TableCell>
              <TableCell>{c.sent_count}</TableCell>
              <TableCell>{c.bounced_count}</TableCell>
              <TableCell>{c.replied_count}</TableCell>
              <TableCell>{new Date(c.created_at).toLocaleDateString()}</TableCell>
            </TableRow>
          ))}
        </TableBody>
      </Table>
    </>
  );
}

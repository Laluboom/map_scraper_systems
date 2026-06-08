import React from "react";
import { Table, TableHead, TableRow, TableCell, TableBody, Chip, Button, Stack } from "@mui/material";

export default function TraderTable({ traders, onApprove, onReject }) {
  if (!traders.length) return <p>No traders found.</p>;

  return (
    <Table size="small" sx={{ mt: 2 }}>
      <TableHead>
        <TableRow>
          <TableCell>Company</TableCell>
          <TableCell>Email</TableCell>
          <TableCell>Phone</TableCell>
          <TableCell>City</TableCell>
          <TableCell>Country</TableCell>
          <TableCell>Source</TableCell>
          <TableCell>Priority</TableCell>
          <TableCell>Valid</TableCell>
          <TableCell>Status</TableCell>
          <TableCell>Actions</TableCell>
        </TableRow>
      </TableHead>
      <TableBody>
        {traders.map((t) => (
          <TableRow key={t.id}>
            <TableCell>{t.company_name || "—"}</TableCell>
            <TableCell>{t.email || "—"}</TableCell>
            <TableCell>{t.phone || "—"}</TableCell>
            <TableCell>{t.city || "—"}</TableCell>
            <TableCell>{t.country || "—"}</TableCell>
            <TableCell>{t.source || "—"}</TableCell>
            <TableCell>
              {t.priority_flag ? <Chip label="Priority" color="warning" size="small" /> : <Chip label="General" size="small" />}
            </TableCell>
            <TableCell>
              {t.email_valid === null ? "—" : t.email_valid ? <Chip label="Valid" color="success" size="small" /> : <Chip label="Invalid" color="error" size="small" />}
            </TableCell>
            <TableCell><Chip label={t.email_status} size="small" /></TableCell>
            <TableCell>
              <Stack direction="row" spacing={1}>
                {!t.approved && (
                  <Button size="small" variant="contained" color="success" onClick={() => onApprove(t.id)}>Approve</Button>
                )}
                <Button size="small" variant="outlined" color="error" onClick={() => onReject(t.id)}>Reject</Button>
              </Stack>
            </TableCell>
          </TableRow>
        ))}
      </TableBody>
    </Table>
  );
}

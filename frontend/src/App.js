import React from "react";
import { BrowserRouter, Routes, Route, NavLink } from "react-router-dom";
import { AppBar, Toolbar, Typography, Drawer, List, ListItemButton, ListItemText, Box } from "@mui/material";
import Dashboard from "./pages/Dashboard";
import Contacts from "./pages/Contacts";
import Campaigns from "./pages/Campaigns";
import Logs from "./pages/Logs";
import Settings from "./pages/Settings";

const NAV = [
  { label: "Dashboard", path: "/" },
  { label: "Contacts", path: "/contacts" },
  { label: "Campaigns", path: "/campaigns" },
  { label: "Logs", path: "/logs" },
  { label: "Settings", path: "/settings" },
];

const DRAWER_WIDTH = 200;

export default function App() {
  return (
    <BrowserRouter>
      <AppBar position="fixed" sx={{ zIndex: 1300 }}>
        <Toolbar>
          <Typography variant="h6">Supplier Scraper</Typography>
        </Toolbar>
      </AppBar>
      <Drawer variant="permanent" sx={{ width: DRAWER_WIDTH, "& .MuiDrawer-paper": { width: DRAWER_WIDTH, mt: 8 } }}>
        <List>
          {NAV.map((n) => (
            <ListItemButton key={n.path} component={NavLink} to={n.path} end={n.path === "/"}>
              <ListItemText primary={n.label} />
            </ListItemButton>
          ))}
        </List>
      </Drawer>
      <Box component="main" sx={{ ml: `${DRAWER_WIDTH}px`, mt: 8, p: 3 }}>
        <Routes>
          <Route path="/" element={<Dashboard />} />
          <Route path="/contacts" element={<Contacts />} />
          <Route path="/campaigns" element={<Campaigns />} />
          <Route path="/logs" element={<Logs />} />
          <Route path="/settings" element={<Settings />} />
        </Routes>
      </Box>
    </BrowserRouter>
  );
}

import { createTheme } from "@mui/material/styles";

const theme = createTheme({
  palette: {
    mode: "light",
    primary: { main: "#1565c0" },
    secondary: { main: "#e65100" },
  },
  typography: {
    fontFamily: "Inter, Roboto, sans-serif",
  },
});

export default theme;

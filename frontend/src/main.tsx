import React from "react";
import ReactDOM from "react-dom/client";
import { BrowserRouter } from "react-router-dom";
import AnalyticsRouterTracker from "./AnalyticsRouterTracker";
import { AuthProvider } from "./hooks/AuthContext";
import App from "./App";
import "./styles/Global.css";

ReactDOM.createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
    <AuthProvider>
      <BrowserRouter>
        <AnalyticsRouterTracker />
        <App />
      </BrowserRouter>
    </AuthProvider>
  </React.StrictMode>
);
